#!/usr/bin/env python
from contextlib import contextmanager
import argparse
import sys
import sshtunnel
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fermi_blind_search.configuration import get_config
from fermi_blind_search import myLogging

_logger = myLogging.log.getLogger("database")

# will store the engine that will connect to the database
_engine = None

# we need this to handle the tables
Base = declarative_base()

# defines the class that will connect to the database
Session = sessionmaker()


@contextmanager
def database_connection(config):

    if config.get("SSH db tunnel", "remote_host") != '':

        with sshtunnel.SSHTunnelForwarder(config.get("SSH db tunnel", "remote_host"),
                                          ssh_username=config.get("SSH db tunnel", "username"),
                                          host_pkey_directories=[
                                              config.get("SSH db tunnel", "key_directory")],
                                          remote_bind_address=('127.0.0.1',
                                                               int(config.get("SSH db tunnel", "tunnel_port"))),
                                          local_bind_address=('localhost',
                                                              int(config.get('Real time', 'db_port'))),

                                          ):

            db_instance = Database(config)

            try:

                yield db_instance

            except:

                raise

            finally:

                db_instance.close()

    else:

        db_instance = Database(config)

        try:

            yield db_instance

        except:

            raise

        finally:

            db_instance.close()


class Database(object):

    def __init__(self, config):

        global Base
        global Session
        global _engine
        global _logger

        # initialize the engine using parameters from the config file
        if config.get("Real time", "is_sqlite") == "True":
            engine_url = "sqlite:///" + config.get("Real time", "db_path")
        else:
            engine_url = config.get("Real time", "db_dialect") + "://" + config.get("Real time", "db_username") + ":" + \
                         config.get("Real time", "db_password") + "@" + config.get("Real time", "db_host") + ":" + \
                         config.get("Real time", "db_port") + "/" + config.get("Real time", "db_path")

        _logger.debug("Database engine URL: %s" % engine_url)
        _engine = create_engine(engine_url)

        # bind the engine to the Base
        Base.metadata.bind = _engine

        # bind the engine to the session
        Session.configure(bind=_engine)

        self._config = config

    def create_tables(self):

        global _logger

        # create the Analysis and Results tables
        Base.metadata.create_all(_engine)

        _logger.info("Successfully created database tables")

    def delete_analysis_table(self):

        global _logger

        # drop the table from the DB
        try:
            Analysis.__table__.drop()
        except:
            try:
                # another way to drop the table
                Analysis.__table__.drop(_engine)
            except:
                _logger.error('ERROR: Could not delete Analysis Table')
                raise
        else:
            _logger.info("Successfully deleted Analysis table")


    def delete_results_table(self):

        # drop the table from the DB
        try:
            Results.__table__.drop()
        except:
            try:
                # another way to drop the table
                Results.__table__.drop(_engine)
            except:
                _logger.error('ERROR: Could not delete Results Table')
                raise
        else:
            _logger.info("Successfully delete Results table")

    def add_analysis(self, analysis_vals):
        # TODO: which check that analysis_vals contains the correct field?
        # TODO: do we want to add a check that the analysis doesn't already exist?

        assert (analysis_vals['met_start'] is not None and analysis_vals['duration'] is not None and
                analysis_vals['counts'] is not None and analysis_vals['outfile'] is not None and
                analysis_vals['logfile'] is not None), "One of the parameters to enter the analysis into the " \
                                                       "database is missing. Parameters are met_start, duration, " \
                                                       "counts, outfile, and logfile"

        assert isinstance(analysis_vals["counts"], int), "Counts is not an integer"

        try:

            # set the values of the analysis to be added to the table
            new_analysis = Analysis(met_start=analysis_vals['met_start'], duration=analysis_vals['duration'],
                                    counts=analysis_vals['counts'], outfile=analysis_vals['outfile'],
                                    logfile=analysis_vals['logfile'])
            _logger.info("Adding this Analysis to the database: %s" % new_analysis)
        except KeyError:
            _logger.error('ERROR: The analysis you want to add does not have the proper fields!')
            raise
        except:
            raise
        else:
            # open a session, add the analysis to the table, close the session
            session = Session()
            session.add(new_analysis)
            try:
                session.commit()
            except:
                raise
            else:
                _logger.debug("Successfully added analysis to db")

    def update_analysis_counts(self, met_start, duration, new_counts):

        global _logger

        # open a session with the DB
        session = Session()

        # get the analysis to be updated
        results = session.query(Analysis).filter(Analysis.met_start == met_start).filter(Analysis.duration == duration).all()

        # check that there is only one analysis that matches these parameters

        assert len(results) == 1, 'More than one analysis exists with these parameters! This should never happen'

        analysis = results[0]

        _logger.info("Updating this analysis: %s to have %s counts" % (analysis, new_counts))

        # update the counts column of the analysis in question
        analysis.counts = new_counts

        try:
            # commit the change
            session.commit()
        except:
            raise
        else:
            _logger.debug("Successfully updated analysis")

    def add_candidate(self, candidate_vals):
        # TODO: which check that condidate_vals contains the correct field?
        # TODO: do we want to add a check that the candidate doesn't already exist?

        global _logger

        assert (candidate_vals['ra'] is not None and candidate_vals['dec'] is not None and
                candidate_vals['met_start'] is not None and candidate_vals['interval'] is not None and
                candidate_vals['email'] is not None), \
            "One of the parameters to enter the candidate into the database is missing. Parameters are ra, dec, " \
            "met_start, interval, email"

        try:
            # set the values of the result to be added to the table
            new_candidate = Results(ra=candidate_vals['ra'], dec=candidate_vals['dec'],
                                    met_start=candidate_vals['met_start'], interval=candidate_vals['interval'],
                                    email=candidate_vals['email'])
            _logger.info("Adding this result to the database %s" % new_candidate)
        except KeyError:
            _logger.error('ERROR: The result you want to add does not have the proper fields')
            raise
        except:
            raise
        else:
            # open a session, add the result to the table, close the session
            session = Session()
            session.add(new_candidate)
            try:
                session.commit()
            except:
                raise
            else:
                _logger.debug("Successfully added result to database")

    def get_analysis_between_times(self, start, stop):

        global _logger

        _logger.info("Fetching analyses using data between %s and %s" % (start, stop))

        # open a session
        session = Session()

        # get all analyses with met_start or met_stop (met_start + duration) times within the range [start,stop]
        return session.query(Analysis).filter(or_(and_(Analysis.met_start >= start, Analysis.met_start <= stop),
                                                      and_(Analysis.met_start + Analysis.duration >= start,
                                                           Analysis.met_start + Analysis.duration <= stop))).all()

    def get_exact_analysis(self, start, stop):

        global _logger

        _logger.info("Fetching analysis with met_start = %s and met_start + duration = %s" % (start, stop))

        # open a session
        session = Session()

        # get all analyses with start time and stop times exactly matching the parameters
        return session.query(Analysis).filter(and_(Analysis.met_start == start,
                                                   Analysis.met_start + Analysis.duration == stop)).all()

    def get_results(self, candidate_vals):

        global _logger

        # check that candidate vals has the correct fields to perform a search
        assert (candidate_vals['ra'] is not None and candidate_vals['dec'] is not None and
                candidate_vals['met_start'] is not None and candidate_vals['interval'] is not None), \
            "One of the parameters to enter the candidate into the database is missing. Parameters are ra, dec, " \
            "met_start, interval"

        # open a session
        session = Session()

        # get the tolerance ranges for determining if we have a match
        ra_tol = float(self._config.get("Real time", "ra_tol"))
        dec_tol = float(self._config.get("Real time", "dec_tol"))
        start_tol = float(self._config.get("Real time", "start_tol"))
        int_tol = float(self._config.get("Real time", "int_tol"))

        _logger.info("Fetching results within %s of ra, %s of dec, %s of met_start, and %s of interval of %s" %
                     (ra_tol, dec_tol, start_tol, int_tol, candidate_vals))

        # get all results that match the passed candidate within a certain tolerance
        return session.query(Results).filter(and_(candidate_vals['ra'] - ra_tol <= Results.ra,
                                                  Results.ra <= candidate_vals['ra'] + ra_tol,
                                                  candidate_vals['dec'] - dec_tol <= Results.dec,
                                                  Results.dec <= candidate_vals['dec'] + dec_tol,
                                                  candidate_vals['met_start'] - start_tol <= Results.met_start,
                                                  Results.met_start <= candidate_vals['met_start'] + start_tol,
                                                  candidate_vals['interval'] - int_tol <= Results.interval,
                                                  Results.interval <= candidate_vals['interval'] + int_tol)).all()

    def get_results_to_email(self):

        global _logger

        _logger.info("Fetching results with email = False (0 in database)")

        # open a session
        session = Session()

        # get all results that have not been emailed yet
        return session.query(Results).filter(Results.email == 0).all()

    def update_result_email(self, candidate, email_val=False):

        global _logger

        _logger.info("Updating result: %s to have email value: %s" % (candidate, email_val))

        # open a session
        session = Session()

        # update the value of the candidate
        candidate.email = email_val

        try:
            # commit the change
            session.commit()
        except:
            raise
        else:
            _logger.debug("Successfully updated result")

    def close(self):

        global _logger

        _logger.info("Closing database")

        Session.close_all()


class Analysis(Base):

    # give the table a name
    __tablename__ = 'analysis'

    # define the columns of the table
    met_start = Column(Float(32), Sequence('analysis_met_start_seq'), primary_key=True)
    duration = Column(Float(32), Sequence('analysis_duration_seq'), primary_key=True)
    counts = Column(Integer)
    outfile = Column(String(250))
    logfile = Column(String(250))

    def __repr__(self):

        # formatting string so that printing rows from the table is more readable
        return "<Analysis(met_start= %s, duration= %s, counts= %s, outfile= %s, logfile= %s)>" % \
               (self.met_start, self.duration, self.counts, self.outfile, self.logfile)


class Results(Base):

    # give the table a name
    __tablename__ = 'results'

    # define the columns of the table
    ra = Column(Float(32))
    dec = Column(Float(32))
    met_start = Column(Float(32), Sequence('results_met_start_seq'), primary_key=True)
    interval = Column(Float(32), Sequence('results_interval_seq'), primary_key=True)
    email = Column(Boolean)

    def __repr__(self):

        # formatting string so that printing rows from the table is more readable
        return "<Results(ra= %s, dec= %s, met_start= %s, interval= %s, email=%s)>" % (self.ra, self.dec,
                                                                                      self.met_start,
                                                                                      self.interval, self.email)


if __name__ == "__main__":

    # Allows you to quickly delete and re-create the database.

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)
    parser.add_argument('--clear', help="If set, delete the database tables, and recreate them", action="store_true")
    args = parser.parse_args()

    configuration = args.config

    # start db connection
    db = Database(configuration)

    if args.clear:
        # delete the tables
        db.delete_analysis_table()
        db.delete_results_table()

        # re-create the tables
        db.create_tables()

