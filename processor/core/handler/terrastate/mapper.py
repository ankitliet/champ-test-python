import json
import argparse
import platform
from pathlib import Path
import os
from sqlalchemy import create_engine, orm
from sqlalchemy.orm import Session
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import re
from sqlalchemy import exc as sqexcp

def dict_to_str(dict):
    response = json.dumps(dict, separators=(",", ":"))
    response = response.replace(":", "=")
    return response
    


Base = declarative_base()


class AutomationRequest(Base):
    __tablename__ = 'automation_request'

    id = Column(Integer, primary_key=True)
    ref_id = Column(String(255), nullable=False)
    task_id = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    status =  Column(String(255), nullable=True)
    created_by =  Column(String(255), nullable=True)
    modified_by =  Column(String(255), nullable=True)
    cloud_provider = Column(String(255), nullable=True)
    
    @classmethod
    def _str(cls):
        return f'{cls.__tablename__}'
    


def create_tf(task_id,tf_file_path,output_file_path,_session):
    try:
        filters = [getattr(AutomationRequest, 'task_id')==task_id]
        filename = tf_file_path
        variables = []
        with open(filename, 'r') as file:
            filedata = file.read()
        with open(filename, 'r') as file:
            Lines = file.readlines()
        for line in Lines:
            if '=' in line:
                arr = line.split('=')
                variables.append(arr[0].strip())


        #variables = re.search(pattern, filedata)
        #print(variables)
        filter_query = _session.query(AutomationRequest).filter(*filters)
        row = filter_query.one()
        data = row.__dict__
        if data['parameters'] is not None:
            parameters = data['parameters']
            for i in variables:
                if i not in parameters:
                    continue
                value = parameters[i]
                if isinstance(value,dict) or isinstance(value,list):
                    value = dict_to_str(value)
                filedata = filedata.replace( "%" + i + "%",str(value))
                #print(filedata)
            filename = output_file_path
            with open(filename, 'w') as file:
                file.write(filedata)
                
        return "Tf file {} generated".format(output_file_path)
    except AttributeError as excp:
        raise Exception(f'Table[{AutomationRequest._str()}] has no column[{excp.__str__().split("attribute ", 1)[1]}]')
    except sqexcp.NoResultFound as excp:
        raise Exception(f'No record for table[{AutomationRequest._str()}] with applied filter[{filters}]were found!')
    except sqexcp.MultipleResultsFound as excp:
        raise Exception(
            f'Multiple records for table[{AutomationRequest._str()}] with applied filter[{filters}] were found! Only one was required!')
    except Exception as ex:
        raise ex
