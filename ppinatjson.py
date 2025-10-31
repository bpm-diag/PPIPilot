import logging
import json
import re

import pandas as pd
import numpy as np
import pm4py
from pm4py.objects.conversion.log import converter as log_converter
import ppinot4py

import streamlit as st

import ppinot4py.model as ppinot
from ppinot4py.model import TimeInstantCondition, RuntimeState, AppliesTo

from datetime import timedelta

import tempfile
import os

def format_time_duration(seconds):
    """Convert seconds to human-readable time format"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:  # Less than 1 hour
        minutes = seconds / 60
        return f"{minutes:.2f} minutes"
    elif seconds < 86400:  # Less than 1 day
        hours = seconds / 3600
        return f"{hours:.2f} hours"
    else:  # 1 day or more
        days = seconds / 86400
        return f"{days:.2f} days"

logger = logging.getLogger(__name__)



def attribute_options(attrib_list, df):
    result_map = { k: values_limit(df[k].unique()) for k in attrib_list }
    return "\n ".join([f"- {k} ({result_map[k]})" for k in result_map])


def values_limit(values, limit = 3):
    values_size = len(values)
    return ", ".join(list(map(str,values))) if values_size <= limit else ", ".join(list(map(str, values[:limit]))) + f", and {values_size-limit} more"


class Log:
    def __init__(self, log, id_case = 'case:concept:name', time_column = 'time:timestamp', activity_column='concept:name'):
        if isinstance(log, pd.DataFrame):
            self.dataframe = log
            self.log = None
        elif isinstance(log, pm4py.objects.log.log.EventLog):
            self.log: pm4py.objects.log.log.EventLog = log
            self.dataframe = None
        else:
            raise RuntimeError("Invalid log")
        
        self.id_case = id_case
        self.time_column = time_column
        self.activity_column = activity_column

    def as_dataframe(self):
        if self.dataframe is None:
            self.dataframe = log_converter.apply(self.log, variant=log_converter.Variants.TO_DATA_FRAME).rename(columns={
                'case:concept:name': self.id_case,
                'time:timestamp': self.time_column,
                'concept:name': self.activity_column
            })
            self.dataframe[self.time_column] = pd.to_datetime(self.dataframe[self.time_column], utc=True)
        else:
            self.dataframe = self.dataframe.rename(columns={
                'case:concept:name': self.id_case,
                'time:timestamp': self.time_column,
                'concept:name': self.activity_column
            })
        #st.write("self.dataframe en as_dataframe", self.dataframe)

        return self.dataframe
    
    def as_eventlog(self):
        if self.log is None:
            parameters = {
                log_converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: self.id_case
            }
            self.log = log_converter.apply(self.dataframe, 
                                           parameters=parameters, 
                                           variant=log_converter.Variants.TO_EVENT_LOG)

        return self.log

def load_log(uploaded_file, id_case='case:concept:name', time_column='time:timestamp', activity_column='concept:name'):
    logger.info("Loading log...")
    
    # Create a temporal file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xes") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    try:
        if uploaded_file.name.endswith('csv'):
            dataframe = pm4py.read_csv(tmp_path)
            log = Log(dataframe, id_case=id_case, time_column=time_column, activity_column=activity_column)
        else:
            log_xes = pm4py.read_xes(tmp_path)
            log = Log(log_xes, id_case=id_case, time_column=time_column, activity_column=activity_column)
    finally:
        os.remove(tmp_path)  # Delete temporal file
    
    logger.info("Log successfully loaded")
    return log

class PPINatJson:
    def __init__(self):
        self.log = None
        self.id_case="ID"
        self.time_column="DATE"
        self.activity_column="ACTIVITY"

    def load_log(self, log):
        #st.write("id_case, time_column, activity_column",self.id_case,self.time_column,self.activity_column)
        LOG = load_log(log, id_case=self.id_case, time_column=self.time_column,
                    activity_column=self.activity_column)
        #st.write("LOG.dataframe", LOG.dataframe)
        
        self.log = LOG.as_dataframe()
        self.log_configuration = ppinot4py.computers.LogConfiguration(id_case=self.id_case, time_column=self.time_column, activity_column=self.activity_column)


    def resolve(self, ppi):
        if "begin" in ppi:
            from_cond = self._transform_condition(ppi["begin"]) if ppi["begin"] else TimeInstantCondition(
                            RuntimeState.START, applies_to=AppliesTo.PROCESS)
            to_cond = self._transform_condition(ppi["end"]) if ppi["end"] else TimeInstantCondition(
                            RuntimeState.END, applies_to=AppliesTo.PROCESS)

            base_metric = ppinot.TimeMeasure(
                        from_condition=from_cond,
                        to_condition=to_cond
                    )

            #aggregation = self._transform_agg(ppi["aggregation"])

        elif "count" in ppi:
            #st.write("Ha entrado aquí")
            count_cond = self._transform_condition(ppi["count"])
            base_metric = ppinot.CountMeasure(count_cond)
            #st.write("base metric", base_metric)
            #aggregation = "AVG"

        if "metric_condition" in ppi and ppi["metric_condition"]:
            base_metric = ppinot.DerivedMeasure(function_expression=f"base {ppi['metric_condition']}",
                                                measure_map = {"base": base_metric})
        
        aggregation = self._transform_agg(ppi["aggregation"])
        other = {}

        if "group_by" in ppi and ppi["group_by"]:
            other["grouper"] = [ppinot.DataMeasure(ppi["group_by"])]

        if "filter" in ppi and ppi["filter"]:
            left, op, right = self._separate_logical_expression(ppi["filter"])

            if left == "activity":
                #st.write("Ha entrado en esta parte del filter (activity)")
                bm = ppinot.CountMeasure(f"`{self.activity_column}` {op} {right}")
                #st.write("bm",bm)
                other["filter_to_apply"] = ppinot.DerivedMeasure(function_expression=f"ma > 0",
                                                            measure_map={"ma": bm})
            elif left in self.log.columns:
                #st.write("Ha entrado en el else del filter")
                bm = ppinot.DataMeasure(left)
                #st.write("bm", bm)
                other["filter_to_apply"] = ppinot.DerivedMeasure(function_expression=f"ma {op} {right}",
                                                            measure_map={"ma": bm})
            else:
                logger.warning(f"Unknown filter: {ppi['filter']}. It will be ignored")

        metric = ppinot.AggregatedMeasure(
            base_measure=base_metric,
            single_instance_agg_function=aggregation,        
            **other
        )

        return metric

    def _transform_condition(self, cond): 
        #st.write("Ha entrado en transform_condition")
        
        # Handle complex conditions with OR operators
        if " or " in cond.lower():
            # Replace 'activity' with the actual column name in the entire expression
            transformed_cond = cond.replace("activity", f"`{self.activity_column}`")
            return transformed_cond
        
        # Handle simple conditions
        left, op, right = self._separate_logical_expression(cond)
        #st.write("Left", left)
        #st.write("op", op)
        #st.write("Right", right)
        if left == "activity":
            left = self.activity_column
        elif left not in self.log.columns:
            logger.warning(f"Unknown condition: {cond}")    
        
        return f"`{left}` {op} {right}"

    def _transform_agg(self, agg):
        if (agg == "average") or (agg == "percentage"):
            return "AVG"
        elif agg == "total":
            return "SUM"
        elif agg == "minimum":
            return "MIN"
        elif agg == "maximum":
            return "MAX"
        else:
            return agg.upper()

    def _separate_logical_expression(self, expression):
        # Use regular expression to find the logical operator
        #st.write("Ha entrado en separate_logical_expression")
        match = re.search(r'(\s*[\w\s:$#{}+\-_]+)\s*([!=<>]+)\s*([\w\s:$#{}+\-_\'\"]+)\s*', expression)
        if match:
            left_side = match.group(1).strip()
            operator = match.group(2).strip()
            right_side = match.group(3).strip()
            return left_side, operator, right_side
        else:
            return None

    def compute(self, metric, time_grouper=None):
        #st.write("Ha entrado en el compute")
        if time_grouper is not None and isinstance(time_grouper, str):
            #st.write("Ha entrado en el if del compute")
            time_grouper = pd.Grouper(freq=time_grouper)
        #st.write("self.log", self.log)
        #st.write("self.configuration", vars(self.log_configuration))
        return ppinot4py.measure_computer(metric, self.log, log_configuration=self.log_configuration, time_grouper=time_grouper)

    def resolve_compute(self, json_ppi, time_grouper=None):
        metric = self.resolve(json_ppi)
        return self.compute(metric, time_grouper=time_grouper)


def process_json(ppi, ppinat, verbose=False, time=None):
    result={}
    error_info = None
    
    if verbose:
        st.write(f"\n{ppi}")

    try:
        metric = ppinat.resolve(ppi["PPIjson"])
        result['metric'] = metric
    except Exception as e:
        error_msg = f"ERROR: processing metric {ppi['PPIjson']} - {str(e)}"
        logger.exception(error_msg)
        error_info = {
            'ppi_name': ppi.get('PPIname', 'Unknown'),
            'ppi_json': ppi['PPIjson'],
            'error_type': 'metric_resolution',
            'error_message': str(e),
            'full_error': error_msg
        }
        result['error'] = error_info
        return result

    if verbose:        
        st.write(f"{metric}")
        if time is not None:
            st.write(f"Time group: {time}")

    try:
        compute_result = ppinat.compute(metric, time_grouper=time)
        result['compute_result'] = compute_result
    except Exception as e:
        error_msg = f"ERROR: computing metric {ppi['PPIjson']} - {str(e)}"
        logger.exception(error_msg)
        error_info = {
            'ppi_name': ppi.get('PPIname', 'Unknown'),
            'ppi_json': ppi['PPIjson'],
            'error_type': 'metric_computation',
            'error_message': str(e),
            'full_error': error_msg
        }
        result['error'] = error_info
    
    return result

def add_row_df(data, name, metric, last_interval, group_by, agrup, agrupation):
    
    data.append({
                    'Name': name, 
                    'Metric': metric,
                    'Last Interval Value': last_interval,  # Suponiendo que 'compute_result' contiene el resultado del cálculo
                    'Group By': group_by,
                    'Agrupation': agrup,
                    'agrupation': agrupation
                                        
                })

    
    return data

def add_row_df_no_time(data, name, metric, value, agrupation):
    
    data.append({
                    'Name': name, 
                    'Metric': metric,
                    'Value': value,  # Suponiendo que 'compute_result' contiene el resultado del cálculo
                    'Agrupation': agrupation,
                                        
                })

    
    return data

def actualizacion_segun_last_valid_value(data,data_sin_error, name, metric, el, ls_def, agrupation,aux ):
    last_valid_value = obtener_ultimo_no_none(aux)
    if last_valid_value is not None:
                                    
        data = add_row_df(data, name, metric, last_valid_value, el, ls_def, agrupation)
        data_sin_error= add_row_df(data_sin_error, name, metric, last_valid_value, el, ls_def, agrupation)

    else:
        last_valid_value = None  # O cualquier otro valor predeterminado que desees
        data = add_row_df(data, name, metric, last_valid_value, el, ls_def, agrupation)
    
    return data,data_sin_error

def calc_agrupation_time(dicc,agrupation,el=None):
    aux=[]
    if el is not None:

        for col_name, col_value in dicc.items():
            if el == col_name[0]:
                aux.append(col_value)
                if pd.isna(col_value):
                    col_value=timedelta(days=0)
                    agrupation.append(col_value.total_seconds())
                # Check if col_value is a large numeric value (likely nanoseconds)
                elif isinstance(col_value, (int, float)) and col_value > 1e6:
                    # Convert from nanoseconds to seconds
                    agrupation.append(col_value / 1e9)
                else:
                    agrupation.append(col_value.total_seconds())
    else:
        for col_name, col_value in dicc.items():
            aux.append(col_value)
            if pd.isna(col_value):
                col_value = timedelta(days=0)
                agrupation.append(col_value.total_seconds())
            # Check if col_value is a large numeric value (likely nanoseconds)
            elif isinstance(col_value, (int, float)) and col_value > 1e6:
                # Convert from nanoseconds to seconds
                agrupation.append(col_value / 1e9)
            else:
                agrupation.append(col_value.total_seconds())

    return agrupation,aux


def exec_final_time(event_log, json_path, time_group=None):
    ppinat = PPINatJson()
    ppinat.load_log(event_log)

    data=[]
    data_sin_error = []
    errors_captured = []

    with open(json_path, "r") as ppis_file:
        ppis = json.load(ppis_file)
    
    for ppi in ppis:

        metric_result = process_json(ppi, ppinat,time = time_group)
        
        # Check for errors first
        if isinstance(metric_result, dict) and 'error' in metric_result:
            errors_captured.append(metric_result['error'])
            continue
            
        if metric_result is not None:  # Verificar si se obtuvo un resultado
            row_added = False
            if  isinstance(metric_result, dict) and 'metric' in metric_result:
                metric = str(metric_result['metric'])
            else:
                metric = metric_result
            metric = changing_names_time(metric)
            if 'compute_result' in metric_result:
                compute_result_value = metric_result['compute_result']
                if hasattr(metric_result['compute_result'], 'iloc'):
                    row_added = True
                    if time_group is not None:
                        agrupation = []
                        
                        if "group0" in metric_result['compute_result'].index.names:
                            ls_group_by = metric_result['compute_result'].index.get_level_values('group0').unique()
                            ls_def=[]
                            for el in ls_group_by:
                                agrupation=[]
                                ls_def.append(el)
                                agrupation,aux = calc_agrupation_time(metric_result['compute_result'],agrupation,el)
                                agrupation = list(agrupation)
                                data, data_sin_error=actualizacion_segun_last_valid_value(data,data_sin_error, ppi['PPIname'], metric, el, ls_def, agrupation,aux )
                                
                        else:
                            agrupation,aux_2 = calc_agrupation_time(metric_result['compute_result'], agrupation)
                            agrupation = list(agrupation)
                            data, data_sin_error=actualizacion_segun_last_valid_value(data,data_sin_error, ppi['PPIname'], metric, '', '', agrupation,aux_2 )

                    else:
                        agrupation = metric_result['compute_result'].to_json()
                        for col_name, col_value in metric_result['compute_result'].items():
                                # Handle different types of values for proper time formatting
                                if isinstance(col_value, timedelta):
                                    seconds = col_value.total_seconds()
                                    display_value = format_time_duration(seconds)
                                elif isinstance(col_value, (int, float)) and col_value > 1e6:
                                    # Large numeric value, likely nanoseconds - convert to seconds then format
                                    seconds = col_value / 1e9
                                    display_value = format_time_duration(seconds)
                                else:
                                    display_value = col_value
                                data = add_row_df_no_time(data, ppi['PPIname'], metric, f"{col_name}:{display_value}",agrupation)
                                data_sin_error = add_row_df_no_time(data_sin_error, ppi['PPIname'], metric, f"{col_name}:{display_value}",agrupation)
                                  
                            
                else:
                    agrupation = ''
            else:
                compute_result_value = None
                agrupation =''
            if row_added==False: 
                if not pd.isna(compute_result_value):
                    # Handle timedelta objects - convert to human-readable time format
                    if isinstance(compute_result_value, timedelta):
                        seconds = compute_result_value.total_seconds()
                        display_value = format_time_duration(seconds)
                    # Handle other types of compute_result_value
                    elif hasattr(compute_result_value, 'iloc') or hasattr(compute_result_value, '__iter__'):
                        # If it's a pandas Series or iterable, get the first value
                        try:
                            if hasattr(compute_result_value, 'iloc'):
                                actual_value = compute_result_value.iloc[0] if len(compute_result_value) > 0 else compute_result_value
                            else:
                                actual_value = next(iter(compute_result_value)) if compute_result_value else compute_result_value
                            # If extracted value is also a timedelta, convert to human-readable format
                            if isinstance(actual_value, timedelta):
                                seconds = actual_value.total_seconds()
                                display_value = format_time_duration(seconds)
                            else:
                                display_value = actual_value
                        except:
                            display_value = compute_result_value
                    else:
                        display_value = compute_result_value
                    
                    data = add_row_df_no_time(data, ppi['PPIname'], metric, display_value,agrupation)
                    data_sin_error = add_row_df_no_time(data_sin_error, ppi['PPIname'], metric, display_value,agrupation)
                    
                else:
                    data = add_row_df_no_time(data, ppi['PPIname'], metric, compute_result_value,agrupation)
    df = pd.DataFrame(data)
    df_sin_error = pd.DataFrame(data_sin_error)
    
    # Remove duplicates based on 'Metric' column, keeping the first occurrence
    df = df.drop_duplicates(subset=['Metric'], keep='first')
    df_sin_error = df_sin_error.drop_duplicates(subset=['Metric'], keep='first')
    
    num_filas = df.shape[0]
    num_filas_sin_error =df_sin_error.shape[0]

    return num_filas, df_sin_error, df, num_filas_sin_error, errors_captured

def exec_final_perc(event_log, json_path, time_group=None):

    ppinat = PPINatJson()
    ppinat.load_log(event_log)

    data=[]
    data_sin_error = []
    errors_captured = []

    with open(json_path, "r") as ppis_file:
        ppis = json.load(ppis_file)

    for ppi in ppis:

        metric_result = process_json(ppi, ppinat,time = time_group)
        
        # Check for errors first
        if isinstance(metric_result, dict) and 'error' in metric_result:
            errors_captured.append(metric_result['error'])
            continue
            
        #st.write("Metric_result", metric_result)
        if metric_result is not None:  # Verificar si se obtuvo un resultado
            row_added = False
            if  isinstance(metric_result, dict) and 'metric' in metric_result:
                metric = str(metric_result['metric'])
                
            else:
                metric = metric_result
            metric = metric_changing_name(metric)
            if 'compute_result' in metric_result:
                compute_result_value = metric_result['compute_result']
                if hasattr(metric_result['compute_result'], 'iloc'):
                    row_added = True
                    if time_group is not None:
                        agrupation = []
                        if "group0" in metric_result['compute_result'].index.names:

                            ls_group_by = metric_result['compute_result'].index.get_level_values('group0').unique()
                            ls_def=[]
                            for el in ls_group_by:
                                agrupation=[]
                                aux =[]
                                ls_def.append(el)

                            for col_name, col_value in metric_result['compute_result'].items():
                                aux.append(col_value)
                                if el == col_name[0]:
                                    if pd.isna(col_value):
                                
                                        col_value = 0

                                    agrupation.append(col_value)
                            agrupation = list(agrupation)

                            last_valid_value = obtener_ultimo_no_none(aux)
                        
                            if last_valid_value is not None:
                                last_valid_value= round(last_valid_value,2)
                                data = add_row_df(data, ppi['PPIname'], metric, last_valid_value,el, ls_def, agrupation)
                                data_sin_error = add_row_df(data_sin_error, ppi['PPIname'], metric, last_valid_value,el, ls_def, agrupation)

                            else:
                                data = add_row_df(data, ppi['PPIname'], metric, last_valid_value,el, ls_def, agrupation)
                                
                        else:
                            aux=[]
                            for col_name, col_value in metric_result['compute_result'].items():
                                aux.append(col_value)
                                if pd.isna(col_value):
                                
                                    col_value = 0

                                agrupation.append(col_value)
                            agrupation = list(agrupation)
                        
                            last_valid_value = obtener_ultimo_no_none(aux)
                            if last_valid_value is not None:
                                last_valid_value= round(last_valid_value,2)
                                data = add_row_df(data, ppi['PPIname'], metric, last_valid_value,'', '', agrupation)
                                data_sin_error = add_row_df(data_sin_error, ppi['PPIname'], metric, last_valid_value,'', '', agrupation)

                            else:
                                data = add_row_df(data, ppi['PPIname'], metric, last_valid_value,'', '', agrupation)
                                
                    else:

                        agrupation = metric_result['compute_result'].to_json()
                        for col_name, col_value in metric_result['compute_result'].items():
                                data = add_row_df_no_time(data,ppi['PPIname'],metric,f"{col_name}:{round(col_value,2)}", agrupation)
                                data_sin_error = add_row_df_no_time(data_sin_error,ppi['PPIname'],metric,f"{col_name}:{round(col_value,2)}", agrupation)
                else:
                    agrupation = ''
            else:
                compute_result_value = None
                agrupation =''
            if row_added==False: 
                if not pd.isna(compute_result_value):
                    data = add_row_df_no_time(data, ppi['PPIname'], metric,round(compute_result_value,2), agrupation )
                    data_sin_error = add_row_df_no_time(data_sin_error, ppi['PPIname'], metric,round(compute_result_value,2), agrupation )
                else:
                    data = add_row_df_no_time(data, ppi['PPIname'], metric,compute_result_value, agrupation )
                
    df = pd.DataFrame(data)
    df_sin_error = pd.DataFrame(data_sin_error)
    
    # Remove duplicates based on 'Metric' column, keeping the first occurrence
    df = df.drop_duplicates(subset=['Metric'], keep='first')
    df_sin_error = df_sin_error.drop_duplicates(subset=['Metric'], keep='first')
    
    num_filas = df.shape[0]
    num_filas_sin_error =df_sin_error.shape[0]

    return num_filas, df_sin_error, df, num_filas_sin_error, errors_captured

def exec_final_both(event_log, json_path_time, json_path_occurrency, time_group=None):
    num_filas, df_sin_error, df, num_filas_sin_error, errors_perc = exec_final_perc(event_log, json_path_occurrency, time_group)
    num_filas2, df_sin_error2, df2, num_filas_sin_error2, errors_time = exec_final_time(event_log, json_path_time, time_group)
    
    # Combine errors from both executions
    errors_combined = errors_perc + errors_time
    
    df_sin_error_def = pd.concat([df_sin_error, df_sin_error2], axis=0)
    df_def = pd.concat([df,df2], axis=0)
    
    # Remove duplicates based on 'Metric' column after concatenation
    df_sin_error_def = df_sin_error_def.drop_duplicates(subset=['Metric'], keep='first')
    df_def = df_def.drop_duplicates(subset=['Metric'], keep='first')
    
    num_filas_total = df_def.shape[0]
    num_filas_sin_error_total = df_sin_error_def.shape[0]
    
    return num_filas_total, df_sin_error_def, df_def, num_filas_sin_error_total, errors_combined

def obtener_ultimo_no_none(lista):
    res = None
    for elemento in reversed(lista):

        if not pd.isna(elemento):
            return elemento
    return res

def metric_changing_name(metric):
    if len(metric.split("'"))>1:
        act1=metric.split("'")[1]
    else:
        act1 = None
    if len(metric.split("'"))>3:
        act2 = metric.split("'")[3]
    else:
        act2=None
    if "the sum of the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1,act2) in metric:
        metric = metric.replace("the sum of the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1,act2),"Number of '{}' activities for cases where activity '{}' does not occur".format(act1,act2))
    
    elif "the sum of the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1,act2) in metric:
        metric = metric.replace("the sum of the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1,act2),"Number of '{}' activities for cases where activity '{}' occurs".format(act1,act2)) 
    
    elif "the sum of the number of times `ACTIVITY` == '{}' filtered by the function ma".format(act1) in metric and "where ma is the last value of '{}'".format(act2):
        metric = metric.replace("the sum of the number of times `ACTIVITY` == '{}' filtered by the function ma".format(act1),"Number of '{}' activities".format(act1))
        metric = metric.replace("where ma is the last value of '{}'".format(act2), "for cases where '{}'".format(act2))
    
    elif "the sum of the number of times `ACTIVITY` == '{}'".format(act1) in metric:
        metric = metric.replace("the sum of the number of times `ACTIVITY` == '{}'".format(act1), "Number of '{}' activities".format(act1))

    elif "the sum of the function base > 0 where base is the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1,act2) in metric:
        metric = metric.replace(metric, "Frequency of activity '{}' for cases where activity '{}' occurs".format(act1,act2))

    elif "the sum of the function base > 0 where base is the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1,act2) in metric:
        metric = metric.replace(metric, "Frequency of activity '{}' for cases where activity '{}' does not occur".format(act1,act2))

    elif "the sum of the function base > 0 where base is the number of times `ACTIVITY` == '{}' grouped by the last value of".format(act1) in metric:
        metric=metric.replace("the sum of the function base > 0 where base is the number of times `ACTIVITY` == '{}' grouped by the last value of".format(act1), "Frequency of activity '{}' grouped by the last value of")  

    elif "the sum of the function base > 0 where base is the number of times `ACTIVITY` == '{}'".format(act1) in metric:
        metric = metric.replace(metric, "Frequency of activity '{}'".format(act1))  
    
    elif "the average of the function base > 0 where base is the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1,act2) in metric:
        metric = metric.replace("the average of the function base > 0 where base is the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1,act2),"Percentage of '{}' out of all '{}'".format(act1,act2))
    
    elif "the average of the function base > 0 where base is the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1,act2) in metric:
        metric = metric.replace("the average of the function base > 0 where base is the number of times `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1,act2),"Percentage of '{}' out of all cases where '{}' does not happen".format(act1,act2))
    
    elif "the average of the function base > 0 where base is the number of times `ACTIVITY` == '{}'".format(act1) in metric:
        metric=metric.replace(metric,"Percentage of '{}' out of all cases".format(act1))

    elif "the average of the number of times `ACTIVITY` == '{}' filtered by the function ma>0 where ma is the number of times `ACTIVITY` == '{}'".format(act1,act2) in metric:
        metric = metric.replace(metric,"Average frequency of activity '{}' for cases where activity '{}' occurs".format(act1,act2))
    
    elif "the average of the number of times `ACTIVITY` == '{}' filtered by the function ma>0 where ma is the number of times `ACTIVITY` != '{}'".format(act1,act2) in metric:
        metric = metric.replace(metric,"Average frequency of activity '{}' for cases where activity '{}' does not occur".format(act1,act2))    

    elif "the average of the number of times `ACTIVITY` == '{}' filtered by the function ma== '{}' where ma is the last value of".format(act1,act2) in metric:
        metric = metric.replace("the average of the number of times `ACTIVITY` == '{}' filtered by the function ma== '{}' where ma is the last value of".format(act1,act2),"Average frequency of activity '{}' for cases where the last value of ".format(act1))
        metric = metric + "is '{}'".format(act2)

    return metric

def changing_names_time(metric):
    if len(metric.split("'"))>1:
        act1=metric.split("'")[1]
    else:
        act1=None
    if len(metric.split("'"))>3:
        act2 = metric.split("'")[3]
    else: 
        act2 = None
    
    if "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "grouped by the last value of" in metric:

        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace("the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <{}PROCESS".format(act1,coincidencias[0]),
                                "The average of the duration between activity '{}' and the end of case".format(act1))
        
    elif "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act2) in metric:

        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace(metric,
                                "The average of the duration between activity '{}' and the end of case where activity '{} does not occur".format(act1,act2))

    elif "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act2) in metric:

        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace(metric,
                                "The average of the duration between activity '{}' and the end of case where activity '{} occurs".format(act1,act2))
        
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act2) in metric:

        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace(metric,
                                "The sum of the duration between activity '{}' and the end of case where activity '{} occurs".format(act1,act2))
        
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act2) in metric:

        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace(metric,
                                "The average of the duration between activity '{}' and the end of case where activity '{} does not occur".format(act1,act2))
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "grouped by the last value of" in metric:

        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace("the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <{}PROCESS".format(act1,coincidencias[0]),"The average of the duration between activity '{}' and the end of case".format(act1))
       
    elif "the minimum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric and "grouped by the last value of" in metric:
        patron = r'<(.*?)PROCESS'
        coincidencias = re.findall(patron, metric)
        metric = metric.replace("the minimum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <{}PROCESS".format(act1,coincidencias[0]),"The average of the duration between activity '{}' and the end of case".format(act1))

    elif "the sum of the duration between the first time instant when <" in metric and "filtered by the function ma" in metric:

        metric = metric.replace(metric, "The sum of the duration between the beginning of the case and activity '{}' for cases where activity '{}' occurs".format(act1,act1))

    elif "the sum of the duration between the first time instant when <" in metric and "and the last time instant when `ACTIVITY` == '{}'".format(act1) in metric:
        metric = metric.replace(metric, "The sum of the duration between the start of the case and activity '{}'".format(act1))    

    elif "the average of the duration between the first time instant when <" in metric and "and the last time instant when `ACTIVITY` == '{}'".format(act1) in metric:
        metric = metric.replace(metric, "The average of the duration between the start of the case and activity '{}'".format(act1))    

    elif "the minimum of the duration between the first time instant when <" in metric and "and the last time instant when `ACTIVITY` == '{}'".format(act1) in metric:
        metric = metric.replace(metric, "The minimum of the duration between the start of the case and activity '{}'".format(act1))    
            
    elif "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1, act2, act2) in metric:
        metric = metric.replace(metric,"The average of the duration between activity {} and activity {} for cases where activity {} occurs".format(act1,act2,act2))
    
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1, act2, act2) in metric:

        metric = metric.replace(metric,"The sum of the duration between activity {} and activity {} for cases where activity {} occurs".format(act1,act2,act2))
        
    elif "the minimum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` == '{}'".format(act1, act2, act2) in metric:
        metric = metric.replace(metric,"The minimum of the duration between activity {} and activity {} for cases where activity {} occurs".format(act1,act2,act2))

    elif "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1, act2, act2) in metric:

        metric = metric.replace(metric,"The average of the duration between activity {} and activity {} for cases where activity {} does not occur".format(act1,act2,act2))
        
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1, act2, act2) in metric:

        metric = metric.replace(metric,"The sum of the duration between activity {} and activity {} for cases where activity {} does not occur".format(act1,act2,act2))
        
    elif "the minimum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}' filtered by the function ma > 0 where ma is the number of times `ACTIVITY` != '{}'".format(act1, act2, act2) in metric:
        metric = metric.replace(metric,"The average of the duration between activity {} and activity {} for cases where activity {} does not occur".format(act1,act2,act2))
       
    elif "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric:
        metric = metric.replace(metric, "The average of the duration between activity {} and the end of the case".format(act1))
        
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric:

        metric = metric.replace(metric, "The sum of the duration between activity {} and the end of the case".format(act1))
      
    elif "the minimum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when <".format(act1) in metric:
        metric = metric.replace(metric, "The minimum of the duration between activity {} and the end of the case".format(act1))
    
    elif "the average of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}'".format(act1,act2) in metric:

        metric = metric.replace(metric,"The average of the duration between activity '{}' and activity '{}'".format(act1,act2))
    
    elif "the sum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}'".format(act1,act2) in metric:

        metric = metric.replace(metric,"The sum of the duration between activity '{}' and activity '{}'".format(act1,act2))
    
    elif "the minimum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}'".format(act1,act2) in metric:

        metric = metric.replace(metric,"The minimum of the duration between activity '{}' and activity '{}'".format(act1,act2))
    
    elif "the maximum of the duration between the first time instant when `ACTIVITY` == '{}' and the last time instant when `ACTIVITY` == '{}'".format(act1,act2) in metric:

        metric = metric.replace(metric,"The maximum of the duration between activity '{}' and activity '{}'".format(act1,act2))

    return metric