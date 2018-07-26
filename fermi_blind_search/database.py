#!/usr/bin/env python

import argparse

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fermi_blind_search.configuration import get_config


# will store the engine that will connect to the database
_engine = None

# we need this to handle the tables
Base = declarative_base()

# defines the class that will connect to the database
Session = sessionmaker()


class Database:

    def __init__(self, config):

        global Base
        global Session
        global _engine

        # initialize the engine using parameters from the config file
        _engine = create_engine(config.get("Real time", "db_engine_url"))

        # bind the engine to the Base
        Base.metadata.bind = _engine

        # bind the engine to the session
        Session.configure(bind=_engine)

    def create_tables(self):

        # create the Analysis and Results tables
        Base.metadata.create_all(_engine)

    def delete_analysis_table(self):

        # drop the table from the DB
        try:
            Analysis.__table__.drop()
        except:
            try:
                # another way to drop the table
                Analysis.__table__.drop(_engine)
            except:
                print('ERROR: Could not delete Analysis Table')
                raise


    def delete_results_table(self):

        # drop the table from the DB
        try:
            Results.__table__.drop()
        except:
            try:
                # another way to drop the table
                Results.__table__.drop(_engine)
            except:
                print('ERROR: Could not delete Results Table')
                raise

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
        except KeyError:
            print('ERROR: The analysis you want to add does not have the proper fields!')
            raise
        # TODO: need to put a catch all except here?
        else:
            # open a session, add the analysis to the table, close the session
            session = Session()
            session.add(new_analysis)
            try:
                session.commit()
            except:
                raise

    def update_analysis_counts(self, met_start, duration, new_counts):

        # open a session with the DB
        session = Session()

        # get the analysis to be updated
        results = session.query(Analysis).filter(Analysis.met_start == met_start).filter(Analysis.duration == duration).all()

        # check that there is only one analysis that matches these parameters
        print("len of results matching query: %s" % len(results))
        assert len(results) == 1, 'More than one analysis exists with these parameters!'

        analysis = results[0]

        # update the counts column of the analysis in question
        analysis.counts = new_counts

        # commit the change
        session.commit()

    def add_candidate(self, candidate_vals):
        # TODO: which check that condidate_vals contains the correct field?
        # TODO: do we want to add a check that the candidate doesn't already exist?

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
        except KeyError:
            print('ERROR: The result you want to add does not have the proper fields')
            raise
        except:
            raise
        # TODO: need to add a catch all except here?
        else:
            # open a session, add the result to the table, close the session
            session = Session()
            session.add(new_candidate)
            session.commit()

    def get_analysis_between_times(self, start, stop):

        # open a session
        session = Session()

        # get all analyses with met_start or met_stop (met_start + duration) times within the range [start,stop]
        return session.query(Analysis).filter(or_(and_(Analysis.met_start >= start, Analysis.met_start <= stop),
                                                      and_(Analysis.met_start + Analysis.duration >= start,
                                                           Analysis.met_start + Analysis.duration <= stop))).all()

    def get_results(self, candidate_vals):
        # TODO: add check to make sure candidate_vals has the correct fields

        # open a session
        session = Session()
        # TODO: change tolerance level to be one that makes sense

        # get all results that match the passed candidate within a certain tolerance
        return session.query(Results).filter(and_(candidate_vals['ra'] - 1 <= Results.ra,
                                                  Results.ra <= candidate_vals['ra'] + 1,
                                                  candidate_vals['dec'] - 1 <= Results.dec,
                                                  Results.dec <= candidate_vals['dec'] + 1,
                                                  candidate_vals['met_start'] - 10 <= Results.met_start,
                                                  Results.met_start <= candidate_vals['met_start'] + 10,
                                                  candidate_vals['interval'] - 10 <= Results.interval,
                                                  Results.interval <= candidate_vals['interval'] + 10)).all()

    def get_results_to_email(self):
        session = Session()

        return session.query(Results).filter(Results.email == 0).all()

    def update_result_email(self, candidate, email_val=False):

        # open a session
        session = Session()

        # update the value of the candidate
        candidate.email = email_val

        # commit the change
        session.commit()


class Analysis(Base):

    # give the table a name
    __tablename__ = 'analysis'

    # define the columns of the table
    met_start = Column(Float, Sequence('analysis_met_start_seq'), primary_key=True)
    duration = Column(Float, Sequence('analysis_duration_seq'), primary_key=True)
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
    ra = Column(Float)
    dec = Column(Float)
    met_start = Column(Float, Sequence('results_met_start_seq'), primary_key=True)
    interval = Column(Float, Sequence('results_interval_seq'), primary_key=True)
    email = Column(Boolean)

    def __repr__(self):

        # formatting string so that printing rows from the table is more readable
        return "<Results(ra= %s, dec= %s, met_start= %s, interval= %s, email=%s)>" % (self.ra, self.dec,
                                                                                      self.met_start,
                                                                                      self.interval, self.email)


if __name__ == "__main__":

    # TODO: remove the main class - used right now for testing

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)

    args = parser.parse_args()

    configuration = args.config

    db = Database(configuration)
    db.create_tables()
