#!/usr/bin/env python

import argparse

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from fermi_blind_search.configuration import get_config


# # create an engine that will connect to the database
# engine = create_engine('sqlite:///test_db1.db', echo=True)
#
# # we need this to handle the tables
# Base = declarative_base()
# Base.metadata.bind = engine
#
# # defines the class that will connect to the database
# Session = sessionmaker(bind=engine)

# create an engine that will connect to the database
_engine = None

# we need this to handle the tables
Base = declarative_base()
# Base.metadata.bind = engine

# defines the class that will connect to the database
Session = sessionmaker()



class Database:

    def __init__(self, configuration):

        global Base
        global Session
        global _engine

        _engine = create_engine(configuration.get("Real time", "db_engine_url"))
        Base.metadata.bind = _engine
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
        # TODO: add check to make sure analysis_vals has the correct fields
        # TODO: do we want to add a check that the analysis doesn't already exist?

        try:

            # set the values of the analysis to be added to the table
            new_analysis = Analysis(met_start=analysis_vals['met_start'], duration=analysis_vals['duration'],
                                counts=analysis_vals['counts'], outfile=analysis_vals['outfile'],
                                logfile=analysis_vals['logfile'])
        except KeyError:
            print('ERROR: The analysis you want to add does not have the proper fields!')
            raise
        else:
            # open a session, add the analysis to the table, close the session
            session = Session()
            session.add(new_analysis)
            session.commit()

    def update_analysis_counts(self, analysis, new_counts):

        # open a session with the DB
        session = Session()

        # update the counts column of the analysis in question
        analysis.counts = new_counts

        # commit the change
        session.commit()

    def add_candidate(self, candidate_vals):
        # TODO: add check to make sure candidate_vals has the correct fields
        # TODO: do we want to add a check that the candidate doesn't already exist?

        try:
            # set the values of the result to be added to the table
            new_candidate = Results(ra=candidate_vals['ra'], dec=candidate_vals['dec'],
                                    met_start=candidate_vals['met_start'], interval=candidate_vals['interval'])
        except KeyError:
            print('ERROR: The result you want to add does not have the proper fields')
            raise
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
                                                  Results.interval <= candidate_vals['interval'] + 10))


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

    def __repr__(self):

        # formatting string so that printing rows from the table is more readable
        return "<Results(ra= %s, dec= %s, met_start= %s, interval= %s)>" % (self.ra, self.dec, self.met_start, self.interval)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Path to config file', type=get_config, required=True)

    args = parser.parse_args()

    configuration = args.config

    db = Database(configuration)
    db.create_tables()

    analysis_to_add = {'met_start': .5, 'duration': 300.2, 'counts': 400, 'outfile': 'woohoo/out.txt',
                       'logfile': 'woohoo/log.txt'}
    # another = {'met_start': .5, 'duration': 305.2, 'counts': 400, 'outfile': 'woohoo/out.txt',
    #                    'logfile': 'woohoo/log.txt'}

    db.add_analysis(analysis_to_add)
    # db.add_analysis(another)

