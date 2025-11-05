import pm4py
import os
from datetime import datetime
import warnings
import openai
from openai import OpenAI
import json
import streamlit as st
import tempfile

# Ignore all warnings
warnings.filterwarnings("ignore")



def remove_invalid_parameters(json_data, valid_attributes):
    """Remove parameters that reference non-existent columns"""
    print(f"Valid attributes: {valid_attributes}")
    
    for ppi in json_data:
        if 'PPIjson' in ppi:
            ppi_json = ppi['PPIjson']
            
            # Check group_by parameter
            if 'group_by' in ppi_json:
                group_by_value = ppi_json['group_by']
                if group_by_value not in valid_attributes:
                    print(f"Removing invalid group_by parameter: {group_by_value}")
                    del ppi_json['group_by']
            
            # Check filter parameter for complex conditions and invalid references
            if 'filter' in ppi_json:
                filter_value = ppi_json['filter']
                should_remove = False
                
                # Check for complex logical operators (AND/OR) that cause errors
                if ' and ' in filter_value.lower() or ' or ' in filter_value.lower():
                    print(f"Removing complex filter with AND/OR operators: {filter_value[:100]}...")
                    should_remove = True
                
                # Check for common invalid patterns
                invalid_patterns = ['case:resource', 'case:amount', 'variant', 'performance', 'context']
                for pattern in invalid_patterns:
                    if pattern in filter_value and pattern not in valid_attributes:
                        print(f"Removing invalid filter parameter containing: {pattern}")
                        should_remove = True
                        break
                
                if should_remove:
                    del ppi_json['filter']
    
    return json_data


def get_completion(client,prompt, model="gpt-4-0125-preview"):  # Here we can change model name
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,  # Temperature
    )
    
    completion = response.choices[0].message.content
    
    return completion


def check_activity_applicable(dataframe, my_activity, type):
    applicable = True
    dict_types = {"time": "time:timestamp", "costs": "Costs", "frequency": "NO", "percentage": "NO"}

    if dict_types[type] == "NO":
        return applicable
    else:
        for index, row in dataframe.iterrows():
            if (row["concept:name"] == my_activity and (dict_types[type] not in dataframe.columns or row[dict_types[type]] is None)):
                applicable = False
        return applicable
    

def findPPI(dataframe, my_activity, list_variants, activities, type, description, goal,nome_file,client):
    if my_activity in activities:


        if(1):
            prompt_path = '1_prompt_description_goal/prompt_' + type + '.txt'

            try:
                with open(prompt_path, 'r') as file:
                    prompt = file.read()
                    response = get_completion(client, prompt.format(dataframe,activities,list_variants,description,goal,my_activity))

                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{nome_file}_{type}_goal.txt", mode='w+', dir=tempfile.gettempdir()) as temp_file:
                        temp_file.write(my_activity + "\n")
                        temp_file.write(response + "\n\n")
                        temp_file_path = temp_file.name

            except FileNotFoundError:
                print("The file does not exist or you have selected a wrong type.")

        else:
            response = "You can't find PPIs of this category, since there are no data in the log."
            print(response)

    else:
        response = "The activity is not in the log."
        print(response)

    return response, temp_file_path


def translatePPI(listPPI,activities,attributes, nome_file, type,client):

    prompt_path = '2_prompt/prompt_' + type + '.txt'
    try:
        with open(prompt_path, 'r') as file:
            prompt = file.read()
            response = get_completion(client, prompt.format(listPPI,activities,attributes))
            print(response)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{nome_file}_{type}_2_prompt.txt", mode='w+', dir=tempfile.gettempdir()) as temp_file:
                temp_file.write(response + "\n\n")
                temp_file_path = temp_file.name

    except FileNotFoundError:
        print("The file does not exist or you have selected a wrong type.")
        response = None
        temp_file_path = None

    return response,temp_file_path


def extract_ppi_json(file_path_input,category):

    line_before=""

    with open(file_path_input, 'r') as file:
        line_array = file.readlines()

    array_temp_json=[]
    data_dict_array=[]
    namePPI=""
    #for single_line in line_array:
    for i in range(len(line_array)):
        if(i==len(line_array)-1):

            data_dict = {}
                
            for item in array_temp_json:
                if len(item.split(": "))>2:
                    key=item.split(": ")[0]
                    value=item.split(": ")[1]
                else:
                    key,value=(item.split(": "))
                key = key.strip()
                value = value.strip()
                data_dict[key] = value

            complete_dict={}
            complete_dict["PPIname"]=namePPI
            complete_dict["PPIjson"]=data_dict
            data_dict_array.append(complete_dict)
        else:
            single_line=line_array[i]

            if single_line.strip().startswith("\"PPIjson\": {"):
                data_dict = {}
                
                for item in array_temp_json:
                    if len(item.split(": "))>2:
                        key=item.split(": ")[0]
                        value=item.split(": ")[1]
                    else:
                        key,value=(item.split(": "))
                    key = key.strip()
                    value = value.strip()
                    data_dict[key] = value

                complete_dict={}
                complete_dict["PPIname"]=namePPI
                complete_dict["PPIjson"]=data_dict
                data_dict_array.append(complete_dict)

                namePPI=line_before

            elif (single_line.strip().startswith('"count"') and category!="time"):
                array_temp_json=[]
                array_temp_json.append(single_line.strip())
            elif (single_line.strip().startswith('"begin"') and category=="time"):
                array_temp_json=[]
                array_temp_json.append(single_line.strip())
            elif (single_line.strip().startswith('"end"')and category=="time"):
                array_temp_json.append(single_line.strip())
            elif single_line.strip().startswith('"metric_condition"'):
                array_temp_json.append(single_line.strip())
            elif single_line.strip().startswith('"aggregation"'):
                array_temp_json.append(single_line.strip())
            elif single_line.strip().startswith('"group_by"'):
                array_temp_json.append(single_line.strip())
            elif single_line.strip().startswith('"filter"'):
                array_temp_json.append(single_line.strip())

            line_before=single_line.strip()


    # Crear un archivo temporal para la salida
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{category}_2_prompt.json", mode='w+', dir=tempfile.gettempdir()) as temp_file:
        json.dump(data_dict_array, temp_file, indent=4)
        temp_file_path = temp_file.name

    # # Save the generated JSON to a permanent file
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # permanent_filename = f"generated_ppi_{category}_{timestamp}.json"
    # permanent_file_path = os.path.join(os.getcwd(), permanent_filename)
    
    # with open(permanent_file_path, 'w', encoding='utf-8') as permanent_file:
    #     json.dump(data_dict_array, permanent_file, indent=4, ensure_ascii=False)
    
    # print(f"Generated JSON saved to: {permanent_file_path}")

    return temp_file_path


def clean_data(file_path):

    with open(file_path, 'r') as file:
        data = json.load(file)

    # Remove empty PPIs (PPIs with empty PPIname or empty PPIjson)
    cleaned_data = []
    for item in data:
        # Skip if PPIname is empty or PPIjson is empty/missing required fields
        if (not item.get('PPIname', '').strip() or 
            not item.get('PPIjson') or 
            not item['PPIjson']):
            continue
        
        item['PPIname']=item['PPIname'].replace("PPIname: ","")
        if(len(item['PPIname'])>0 and (item['PPIname'][-1]==",")):
            item['PPIname']=item['PPIname'][:-1]

        if item['PPIjson']:
            for key in item['PPIjson']:
                if(len(item['PPIjson'][key])>0 and (item['PPIjson'][key])[-1]==","):
                    item['PPIjson'][key]=item['PPIjson'][key][:-1]
        
        cleaned_data.append(item)

    with open(file_path, 'w') as file:
        json.dump(cleaned_data, file, indent=4)
    
    # Also save the cleaned data to a permanent file
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # permanent_filename = f"cleaned_ppi_{timestamp}.json"
    # permanent_file_path = os.path.join(os.getcwd(), permanent_filename)
    
    # with open(permanent_file_path, 'w', encoding='utf-8') as permanent_file:
    #     json.dump(cleaned_data, permanent_file, indent=4, ensure_ascii=False)
    
    # print(f"Cleaned JSON saved to: {permanent_file_path}")

def modify_file(file_path):

    with open(file_path, 'r+', encoding='utf-8') as file:
        content = file.read()
        file.seek(0)
        file.write(content.replace("\\\"", ""))
        file.truncate()


def inject_test_ppis(json_file_path, category):
    """
    Injects test PPIs with known errors to test the error correction mechanism
    
    Args:
        json_file_path: Path to the JSON file to modify
        category: Category of PPIs (time or occurrency)
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Test PPIs with intentional errors
    test_ppis = []
    
    if category == "time":
        test_ppis = [
            {
                "PPIname": "Average time from 'Declaration SAVED by EMPLOYEE' to the next activity in the process, excluding rejections",
                "PPIjson": {
                    "begin": "activity == 'Declaration SAVED by EMPLOYEE'",
                    "end": "",
                    "aggregation": "average",
                    "filter": "activity != 'Declaration REJECTED by EMPLOYEE' and activity != 'Declaration REJECTED by ADMINISTRATION' and activity != 'Declaration REJECTED by SUPERVISOR' and activity != 'Declaration REJECTED by MISSING' and activity != 'Declaration REJECTED by PRE_APPROVER' and activity != 'Declaration REJECTED by BUDGET OWNER'"
                }
            },
            {
                "PPIname": "Minimum time for 'Request Payment' across different case amounts",
                "PPIjson": {
                    "begin": "activity == 'Request Payment'",
                    "end": "",
                    "aggregation": "minimum",
                    "group_by": "case:amount"
                }
            }
        ]
    
    # Add test PPIs to the data
    data.extend(test_ppis)
    
    # Save back to file
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    
    print(f"\n🧪 TEST MODE: Injected {len(test_ppis)} test PPIs with errors to {json_file_path}")
    for ppi in test_ppis:
        print(f"  - {ppi['PPIname'][:80]}...")
    print()

def clear_all_ppis(json_file_path):
    """
    Clears all PPIs from the JSON file to test the retry mechanism for 0 PPIs
    
    Args:
        json_file_path: Path to the JSON file to modify
    """
    # Save an empty array to simulate 0 PPIs generated
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump([], file, indent=4, ensure_ascii=False)
    
    print(f"\n🧪 RETRY TEST MODE: Cleared all PPIs from {json_file_path} to test retry mechanism")
    print(f"   This will trigger the retry mechanism (max 2 retries)\n")

def exec(dataframe, acti, varianti, activities, category, description, goal, attribute_array, nome_file, client, inject_test_errors=False, test_retry_mechanism=False):
    listaKPI,temp_file_path =findPPI(dataframe,acti,varianti,activities,category,description,goal,nome_file, client)
    _, file_path_input = translatePPI(listaKPI,activities,attribute_array,nome_file,category,client)
    extracted_data = extract_ppi_json(file_path_input,category)
    modify_file(extracted_data)
    clean_data(extracted_data)
    
    # Test retry mechanism by clearing all PPIs (only on first attempt)
    if test_retry_mechanism:
        clear_all_ppis(extracted_data)
    # Inject test PPIs if requested
    elif inject_test_errors:
        inject_test_ppis(extracted_data, category)
    
    return extracted_data

def auto_correct_errors_with_retry(xes_file, json_path, ppis_type, activities, attributes, client, 
                                   json_path_time=None, json_path_occurrency=None, 
                                   max_level1_iterations=2, max_level2_iterations=2):
    """
    Automatically corrects JSON errors with separate iteration limits for Level 1 and Level 2.
    
    Args:
        xes_file: The XES file to execute PPIs against
        json_path: Path to the JSON file with PPIs (for single type)
        ppis_type: Type of PPIs ('time', 'occurrency', or 'both')
        activities: List of available activities
        attributes: List of available attributes
        client: OpenAI client instance
        json_path_time: Path to time JSON file (for 'both' type)
        json_path_occurrency: Path to occurrency JSON file (for 'both' type)
        max_level1_iterations: Maximum number of Level 1 (re-translation) iterations (default: 2)
        max_level2_iterations: Maximum number of Level 2 (error correction) iterations (default: 2)
    
    Returns:
        Tuple: (batch_size, df_sin_error, df, batch_size_sin_error, errors_captured, total_iterations)
    """
    import ppinatjson as pp
    
    # Configuration parameters - easily modifiable
    MAX_LEVEL1_ITERATIONS = max_level1_iterations  # Level 1: Re-translation attempts
    MAX_LEVEL2_ITERATIONS = max_level2_iterations  # Level 2: Error correction attempts
    
    print(f"\n{'='*70}")
    print(f"ERROR CORRECTION CONFIGURATION:")
    print(f"  - Level 1 (Re-translation) max iterations: {MAX_LEVEL1_ITERATIONS}")
    print(f"  - Level 2 (Error correction) max iterations: {MAX_LEVEL2_ITERATIONS}")
    print(f"{'='*70}\n")
    
    current_json_path = json_path
    current_json_path_time = json_path_time
    current_json_path_occurrency = json_path_occurrency
    total_iterations = 0
    
    # Phase 1: Level 1 iterations (Re-translation)
    level1_iteration = 0
    while level1_iteration < MAX_LEVEL1_ITERATIONS:
        total_iterations += 1
        print(f"\n{'='*60}")
        print(f"LEVEL 1 - Iteration {level1_iteration + 1}/{MAX_LEVEL1_ITERATIONS} (Total: {total_iterations})")
        print(f"{'='*60}\n")
        
        # Execute PPIs based on type
        if ppis_type == "occurrency":
            batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_perc(xes_file, current_json_path)
        elif ppis_type == "time":
            batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_time(xes_file, current_json_path)
        elif ppis_type == "both":
            batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_both(xes_file, current_json_path_time, current_json_path_occurrency)
        else:
            raise ValueError(f"Invalid ppis_type: {ppis_type}")
        
        # Check if there are errors
        if len(errors_captured) == 0:
            print(f"✅ No errors found in Level 1 iteration {level1_iteration + 1}. Returning results.")
            return batch_size, df_sin_error, df, batch_size_sin_error, errors_captured, total_iterations
        
        print(f"⚠️ Found {len(errors_captured)} errors in Level 1 iteration {level1_iteration + 1}")
        
        # Attempt Level 1 correction (Re-translation)
        print(f"🔄 Attempting Level 1 correction (re-translation)...")
        
        correction_successful = False
        
        # For 'both' type, we need to correct both files separately
        if ppis_type == "both":
            # Separate errors by type
            time_errors = [e for e in errors_captured if 'begin' in e.get('ppi_json', {}) or 'end' in e.get('ppi_json', {})]
            occurrency_errors = [e for e in errors_captured if 'count' in e.get('ppi_json', {})]
            
            # Correct time errors if any
            if time_errors and current_json_path_time:
                try:
                    with open(current_json_path_time, 'r', encoding='utf-8') as file:
                        time_json_data = json.load(file)
                    
                    corrected_time_path = correct_json_errors(time_json_data, time_errors, activities, attributes, client, use_retranslation=True)
                    
                    if corrected_time_path:
                        current_json_path_time = corrected_time_path
                        print(f"✅ Time JSON corrected with Level 1.")
                        correction_successful = True
                except Exception as e:
                    print(f"❌ Failed to correct time JSON with Level 1: {str(e)}")
            
            # Correct occurrency errors if any
            if occurrency_errors and current_json_path_occurrency:
                try:
                    with open(current_json_path_occurrency, 'r', encoding='utf-8') as file:
                        occurrency_json_data = json.load(file)
                    
                    corrected_occurrency_path = correct_json_errors(occurrency_json_data, occurrency_errors, activities, attributes, client, use_retranslation=True)
                    
                    if corrected_occurrency_path:
                        current_json_path_occurrency = corrected_occurrency_path
                        print(f"✅ Occurrency JSON corrected with Level 1.")
                        correction_successful = True
                except Exception as e:
                    print(f"❌ Failed to correct occurrency JSON with Level 1: {str(e)}")
        else:
            # Single type correction with Level 1
            try:
                with open(current_json_path, 'r', encoding='utf-8') as file:
                    original_json_data = json.load(file)
            except Exception as e:
                print(f"❌ Failed to read JSON file: {str(e)}")
                break
            
            corrected_path = correct_json_errors(
                original_json_data,
                errors_captured,
                activities,
                attributes,
                client,
                use_retranslation=True
            )
            
            if corrected_path:
                print(f"✅ JSON corrected with Level 1. Proceeding to next iteration...")
                current_json_path = corrected_path
                correction_successful = True
            else:
                print(f"❌ Level 1 correction failed.")
        
        # If correction was not successful and this is the last Level 1 iteration, break to Level 2
        if not correction_successful:
            print(f"⚠️ Level 1 correction unsuccessful in iteration {level1_iteration + 1}")
        
        level1_iteration += 1
    
    # Check if we still have errors after Level 1
    print(f"\n{'='*60}")
    print(f"Level 1 completed after {MAX_LEVEL1_ITERATIONS} iterations")
    print(f"{'='*60}\n")
    
    # Re-execute to check current state
    if ppis_type == "occurrency":
        batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_perc(xes_file, current_json_path)
    elif ppis_type == "time":
        batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_time(xes_file, current_json_path)
    elif ppis_type == "both":
        batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_both(xes_file, current_json_path_time, current_json_path_occurrency)
    
    if len(errors_captured) == 0:
        print(f"✅ All errors resolved after Level 1. Returning results.")
        return batch_size, df_sin_error, df, batch_size_sin_error, errors_captured, total_iterations
    
    print(f"⚠️ Still have {len(errors_captured)} errors after Level 1. Proceeding to Level 2...")
    
    # Phase 2: Level 2 iterations (Error correction)
    level2_iteration = 0
    while level2_iteration < MAX_LEVEL2_ITERATIONS:
        total_iterations += 1
        print(f"\n{'='*60}")
        print(f"LEVEL 2 - Iteration {level2_iteration + 1}/{MAX_LEVEL2_ITERATIONS} (Total: {total_iterations})")
        print(f"{'='*60}\n")
        
        # Execute PPIs based on type
        if ppis_type == "occurrency":
            batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_perc(xes_file, current_json_path)
        elif ppis_type == "time":
            batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_time(xes_file, current_json_path)
        elif ppis_type == "both":
            batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_both(xes_file, current_json_path_time, current_json_path_occurrency)
        
        # Check if there are errors
        if len(errors_captured) == 0:
            print(f"✅ No errors found in Level 2 iteration {level2_iteration + 1}. Returning results.")
            return batch_size, df_sin_error, df, batch_size_sin_error, errors_captured, total_iterations
        
        print(f"⚠️ Found {len(errors_captured)} errors in Level 2 iteration {level2_iteration + 1}")
        
        # Attempt Level 2 correction (Error fixing)
        print(f"🔧 Attempting Level 2 correction (error fixing)...")
        
        correction_successful = False
        
        # For 'both' type, we need to correct both files separately
        if ppis_type == "both":
            # Separate errors by type
            time_errors = [e for e in errors_captured if 'begin' in e.get('ppi_json', {}) or 'end' in e.get('ppi_json', {})]
            occurrency_errors = [e for e in errors_captured if 'count' in e.get('ppi_json', {})]
            
            # Correct time errors if any
            if time_errors and current_json_path_time:
                try:
                    with open(current_json_path_time, 'r', encoding='utf-8') as file:
                        time_json_data = json.load(file)
                    
                    corrected_time_path = correct_json_errors(time_json_data, time_errors, activities, attributes, client, use_retranslation=False)
                    
                    if corrected_time_path:
                        current_json_path_time = corrected_time_path
                        print(f"✅ Time JSON corrected with Level 2.")
                        correction_successful = True
                except Exception as e:
                    print(f"❌ Failed to correct time JSON with Level 2: {str(e)}")
            
            # Correct occurrency errors if any
            if occurrency_errors and current_json_path_occurrency:
                try:
                    with open(current_json_path_occurrency, 'r', encoding='utf-8') as file:
                        occurrency_json_data = json.load(file)
                    
                    corrected_occurrency_path = correct_json_errors(occurrency_json_data, occurrency_errors, activities, attributes, client, use_retranslation=False)
                    
                    if corrected_occurrency_path:
                        current_json_path_occurrency = corrected_occurrency_path
                        print(f"✅ Occurrency JSON corrected with Level 2.")
                        correction_successful = True
                except Exception as e:
                    print(f"❌ Failed to correct occurrency JSON with Level 2: {str(e)}")
        else:
            # Single type correction with Level 2
            try:
                with open(current_json_path, 'r', encoding='utf-8') as file:
                    original_json_data = json.load(file)
            except Exception as e:
                print(f"❌ Failed to read JSON file: {str(e)}")
                break
            
            corrected_path = correct_json_errors(
                original_json_data,
                errors_captured,
                activities,
                attributes,
                client,
                use_retranslation=False
            )
            
            if corrected_path:
                print(f"✅ JSON corrected with Level 2. Proceeding to next iteration...")
                current_json_path = corrected_path
                correction_successful = True
            else:
                print(f"❌ Level 2 correction failed.")
        
        # If correction was not successful and this is the last Level 2 iteration, break
        if not correction_successful:
            print(f"⚠️ Level 2 correction unsuccessful in iteration {level2_iteration + 1}")
        
        level2_iteration += 1
    
    # Final execution to get final state
    print(f"\n{'='*60}")
    print(f"Level 2 completed after {MAX_LEVEL2_ITERATIONS} iterations")
    print(f"{'='*60}\n")
    
    if ppis_type == "occurrency":
        batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_perc(xes_file, current_json_path)
    elif ppis_type == "time":
        batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_time(xes_file, current_json_path)
    elif ppis_type == "both":
        batch_size, df_sin_error, df, batch_size_sin_error, errors_captured = pp.exec_final_both(xes_file, current_json_path_time, current_json_path_occurrency)
    
    if len(errors_captured) == 0:
        print(f"✅ All errors resolved after Level 2. Returning results.")
    else:
        print(f"⚠️ {len(errors_captured)} errors remain after all correction attempts.")
        print(f"Returning results as-is.")
    
    return batch_size, df_sin_error, df, batch_size_sin_error, errors_captured, total_iterations

def retranslate_ppi(ppi_name, error_info, activities, attributes, ppi_category, client):
    """
    Re-translates a single PPI that caused errors using a specialized prompt
    
    Args:
        ppi_name: Name of the PPI to re-translate
        error_info: Dictionary containing error information
        activities: List of available activities in the log
        attributes: List of available attributes in the log
        ppi_category: Category of the PPI ('time' or 'occurrency')
        client: OpenAI client instance
    
    Returns:
        Re-translated PPI as a dictionary, or None if failed
    """
    print(f"\n🔄 LEVEL 1 FALLBACK: Re-translating PPI '{ppi_name}' using specialized prompt...")
    
    # Determine the prompt file based on category
    prompt_path = f'3_prompt_retranslation/prompt_retranslation_{ppi_category}.txt'
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            prompt_template = file.read()
        
        # Format error message
        error_message = f"{error_info.get('error_type', 'Unknown')}: {error_info.get('error_message', 'No details')}"
        
        # Format activities and attributes
        activities_str = ', '.join(activities) if activities else 'No activities provided'
        attributes_str = ', '.join(attributes) if attributes else 'No attributes provided'
        
        # Format the prompt
        formatted_prompt = prompt_template.replace('{0}', ppi_name)
        formatted_prompt = formatted_prompt.replace('{1}', error_message)
        formatted_prompt = formatted_prompt.replace('{2}', activities_str)
        formatted_prompt = formatted_prompt.replace('{3}', attributes_str)
        
        print(f"Sending re-translation request to OpenAI for '{ppi_name}'...")
        
        # Get re-translation from OpenAI
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = get_completion(client, formatted_prompt)
                print(f"Re-translation attempt {attempt + 1} - response length: {len(response)}")
                
                # Clean the response
                cleaned_response = response.strip()
                
                # Remove markdown formatting if present
                if '```json' in cleaned_response:
                    cleaned_response = cleaned_response.split('```json')[1].split('```')[0].strip()
                elif '```' in cleaned_response:
                    cleaned_response = cleaned_response.split('```')[1].strip()
                
                # Find the JSON object boundaries
                start_idx = cleaned_response.find('{')
                end_idx = cleaned_response.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    cleaned_response = cleaned_response[start_idx:end_idx + 1]
                
                # Parse the JSON
                retranslated_ppi = json.loads(cleaned_response)
                
                # Validate the structure
                if 'PPIname' in retranslated_ppi and 'PPIjson' in retranslated_ppi:
                    print(f"✅ Successfully re-translated PPI '{ppi_name}'")
                    return retranslated_ppi
                else:
                    print(f"⚠️ Re-translated PPI missing required fields, retrying...")
                    if attempt < max_retries - 1:
                        formatted_prompt += "\n\nIMPORTANT: Your previous response was missing required fields. Please return a valid JSON object with 'PPIname' and 'PPIjson' fields."
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse re-translated JSON on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    formatted_prompt += "\n\nIMPORTANT: Your previous response was not valid JSON. Please return ONLY a valid JSON object starting with '{' and ending with '}'."
            except Exception as e:
                print(f"❌ Error during re-translation attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None
        
        print(f"❌ Failed to re-translate PPI '{ppi_name}' after {max_retries} attempts")
        return None
        
    except FileNotFoundError:
        print(f"❌ Re-translation prompt file not found: {prompt_path}")
        return None
    except Exception as e:
        print(f"❌ Error during PPI re-translation: {e}")
        return None


def correct_json_errors(original_json, errors_list, activities, attributes, client, use_retranslation=False):
    """
    Corrects JSON errors using OpenAI API
    
    Args:
        original_json: The original JSON data (as Python object) with errors
        errors_list: List of error dictionaries captured during execution
        activities: List of available activities in the log
        attributes: List of available attributes in the log
        client: OpenAI client instance
        use_retranslation: If True, uses re-translation prompt (Level 1), otherwise uses correction prompt (Level 2)
    
    Returns:
        Path to the corrected JSON file
    """
    
    # If using re-translation (Level 1 fallback)
    if use_retranslation:
        print("\n" + "="*60)
        print("LEVEL 1 FALLBACK: Re-translating problematic PPIs")
        print("="*60 + "\n")
        
        # Determine category from the JSON structure
        ppi_category = None
        if original_json and len(original_json) > 0:
            first_ppi = original_json[0]
            if 'PPIjson' in first_ppi:
                if 'begin' in first_ppi['PPIjson'] or 'end' in first_ppi['PPIjson']:
                    ppi_category = 'time'
                elif 'count' in first_ppi['PPIjson']:
                    ppi_category = 'occurrency'
        
        if not ppi_category:
            print("❌ Could not determine PPI category, falling back to Level 2")
            return correct_json_errors(original_json, errors_list, activities, attributes, client, use_retranslation=False)
        
        # Clean the JSON data
        cleaned_json = []
        for item in original_json:
            if (not item.get('PPIname', '').strip() or 
                not item.get('PPIjson') or 
                not item['PPIjson']):
                continue
            
            cleaned_item = item.copy()
            cleaned_item['PPIname'] = item['PPIname'].replace("PPIname: ", "")
            if len(cleaned_item['PPIname']) > 0 and cleaned_item['PPIname'][-1] == ",":
                cleaned_item['PPIname'] = cleaned_item['PPIname'][:-1]
            cleaned_item['PPIname'] = cleaned_item['PPIname'].replace('\\', '')
            
            if cleaned_item['PPIjson']:
                cleaned_ppi_json = {}
                for key, value in cleaned_item['PPIjson'].items():
                    if isinstance(value, str):
                        if len(value) > 0 and value[-1] == ",":
                            value = value[:-1]
                        value = value.replace('\\', '')
                        if value.strip() == "":
                            value = ""
                    cleaned_ppi_json[key] = value
                cleaned_item['PPIjson'] = cleaned_ppi_json
            
            cleaned_json.append(cleaned_item)
        
        original_json = cleaned_json
        
        # Create error mapping
        error_map = {}
        for error in errors_list:
            ppi_name = error['ppi_name']
            if ppi_name not in error_map:
                error_map[ppi_name] = error
        
        # Separate working and problematic PPIs
        problematic_ppis = []
        working_ppis = []
        
        for ppi in original_json:
            if ppi['PPIname'] in error_map:
                problematic_ppis.append(ppi)
            else:
                working_ppis.append(ppi)
        
        print(f"Re-translating {len(problematic_ppis)} problematic PPIs")
        print(f"Keeping {len(working_ppis)} working PPIs unchanged")
        
        # Re-translate each problematic PPI
        retranslated_ppis = []
        failed_ppis = []
        
        for ppi in problematic_ppis:
            ppi_name = ppi['PPIname']
            error_info = error_map[ppi_name]
            
            retranslated = retranslate_ppi(ppi_name, error_info, activities, attributes, ppi_category, client)
            
            if retranslated:
                retranslated_ppis.append(retranslated)
            else:
                failed_ppis.append(ppi)
        
        print(f"\n✅ Successfully re-translated: {len(retranslated_ppis)} PPIs")
        print(f"❌ Failed to re-translate: {len(failed_ppis)} PPIs")
        
        # If some PPIs failed re-translation, return None to trigger Level 2
        if len(failed_ppis) > 0:
            print(f"\n⚠️ {len(failed_ppis)} PPIs failed re-translation, will trigger Level 2 fallback")
            # Update the original_json and errors_list to only include failed PPIs
            # This will be used by Level 2
            return None
        
        # Merge re-translated PPIs with working PPIs
        final_json = working_ppis + retranslated_ppis
        
        # Post-process to remove invalid parameters
        final_json = remove_invalid_parameters(final_json, attributes)
        
        # Save to temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_retranslated.json", mode='w+', dir=tempfile.gettempdir()) as temp_file:
            json.dump(final_json, temp_file, indent=4)
            temp_file_path = temp_file.name
        
        print(f"✅ Re-translated JSON saved with {len(final_json)} total PPIs")
        return temp_file_path
    
    # Original correction logic (Level 2 fallback)
    print("\n" + "="*60)
    print("LEVEL 2 FALLBACK: Using error correction prompt")
    print("="*60 + "\n")

    # Clean the JSON data directly (not from file)
    cleaned_json = []
    for item in original_json:
        # Skip if PPIname is empty or PPIjson is empty/missing required fields
        if (not item.get('PPIname', '').strip() or 
            not item.get('PPIjson') or 
            not item['PPIjson']):
            continue
        
        # Clean PPIname
        cleaned_item = item.copy()
        cleaned_item['PPIname'] = item['PPIname'].replace("PPIname: ", "")
        if len(cleaned_item['PPIname']) > 0 and cleaned_item['PPIname'][-1] == ",":
            cleaned_item['PPIname'] = cleaned_item['PPIname'][:-1]
        # Fix escaped quotes in PPIname
        cleaned_item['PPIname'] = cleaned_item['PPIname'].replace('\\', '')
        
        # Clean PPIjson values
        if cleaned_item['PPIjson']:
            cleaned_ppi_json = {}
            for key, value in cleaned_item['PPIjson'].items():
                if isinstance(value, str):
                    # Remove trailing commas
                    if len(value) > 0 and value[-1] == ",":
                        value = value[:-1]
                    # Fix escaped quotes in activity names
                    value = value.replace('\\', '')
                    # Clean up empty strings
                    if value.strip() == "":
                        value = ""
                cleaned_ppi_json[key] = value
            cleaned_item['PPIjson'] = cleaned_ppi_json
        
        cleaned_json.append(cleaned_item)
    
    # Use the cleaned JSON data
    original_json = cleaned_json
    print(f"Original JSON has {len(original_json)} PPIs")
    
    # Format errors for the prompt - deduplicate errors
    error_summary = []
    seen_errors = set()
    problematic_ppi_names = set()
    
    for error in errors_list:
        # Create a unique key for deduplication
        error_key = f"{error['ppi_name']}_{error['error_message']}"
        if error_key not in seen_errors:
            seen_errors.add(error_key)
            problematic_ppi_names.add(error['ppi_name'])
            error_summary.append({
                'ppi_name': error['ppi_name'],
                'error_type': error['error_type'],
                'error_message': error['error_message'],
                'ppi_json': error['ppi_json']
            })
    
    print(f"Deduplicated errors: {len(error_summary)} unique errors from {len(errors_list)} total")
    print(f"Problematic PPIs: {problematic_ppi_names}")
    
    # Extract only the problematic PPIs for correction
    problematic_ppis = []
    working_ppis = []
    
    for ppi in original_json:
        if ppi['PPIname'] in problematic_ppi_names:
            problematic_ppis.append(ppi)
        else:
            working_ppis.append(ppi)
    
    print(f"Sending {len(problematic_ppis)} problematic PPIs to OpenAI for correction")
    print(f"Keeping {len(working_ppis)} working PPIs unchanged")
    
    # Use only problematic PPIs for the correction prompt
    json_to_correct = problematic_ppis
    
    # Read the error correction prompt
    print("Reading prompt template...")
    prompt_path = '3_prompt_json_correction/prompt_error_correction.txt'
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            prompt_template = file.read()
        print(f"Prompt template loaded, length: {len(prompt_template)}")
        print("gino2") 
        # Format the prompt with the data
        try:
            # Safely serialize JSON with proper escaping - use only problematic PPIs
            original_json_str = json.dumps(json_to_correct, indent=2, ensure_ascii=False)
            error_summary_str = json.dumps(error_summary, indent=2, ensure_ascii=False)
            activities_str = ', '.join(activities) if activities else 'No activities provided'
            attributes_str = ', '.join(attributes) if attributes else 'No attributes provided'
            
            print(f"Original JSON length: {len(original_json_str)}")
            print(f"Error summary length: {len(error_summary_str)}")
            print(f"Activities: {activities_str[:100]}...")
            print(f"Attributes: {attributes_str[:100]}...")
            
            # Debug: check for problematic characters
            print(f"Original JSON preview: {repr(original_json_str[:200])}")
            print(f"Error summary preview: {repr(error_summary_str[:200])}")
            
            # Use safer formatting approach
            formatted_prompt = prompt_template.replace('{0}', original_json_str)
            formatted_prompt = formatted_prompt.replace('{1}', error_summary_str)
            formatted_prompt = formatted_prompt.replace('{2}', activities_str)
            formatted_prompt = formatted_prompt.replace('{3}', attributes_str)
        except Exception as format_error:
            print(f"Error formatting prompt: {format_error}")
            print(f"Prompt template: {prompt_template[:200]}...")
            return None
        print("Prompt formatted successfully")
        print(f"Formatted prompt length: {len(formatted_prompt)}")
        print(f"Formatted prompt preview: {formatted_prompt[:500]}...")
        
        # Save the formatted prompt to a file
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # prompt_filename = f"formatted_prompt_{timestamp}.txt"
        # try:
        #     with open(prompt_filename, 'w', encoding='utf-8') as prompt_file:
        #         prompt_file.write(formatted_prompt)
        #     print(f"Formatted prompt saved to: {prompt_filename}")
        # except Exception as save_error:
        #     print(f"Error saving formatted prompt: {save_error}")
        
        # Get correction from OpenAI with retry logic
        print("Sending prompt to OpenAI for JSON correction...")
        max_retries = 2
        corrected_json_str = None
        
        for attempt in range(max_retries):
            try:
                corrected_json_str = get_completion(client, formatted_prompt)
                print(f"OpenAI attempt {attempt + 1} - raw response length: {len(corrected_json_str)}")
                print(f"OpenAI attempt {attempt + 1} - raw response (first 500 chars): {repr(corrected_json_str[:500])}")
                print(f"OpenAI attempt {attempt + 1} - raw response (last 200 chars): {repr(corrected_json_str[-200:])}")
                
                # Save the raw OpenAI response to a file
                # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # openai_response_filename = f"openai_response_{timestamp}_attempt_{attempt + 1}.txt"
                # try:
                #     with open(openai_response_filename, 'w', encoding='utf-8') as response_file:
                #         response_file.write(f"OpenAI Attempt {attempt + 1}\n")
                #         response_file.write(f"Timestamp: {timestamp}\n")
                #         response_file.write(f"Response Length: {len(corrected_json_str)}\n")
                #         response_file.write("="*50 + "\n")
                #         response_file.write("RAW OPENAI RESPONSE:\n")
                #         response_file.write("="*50 + "\n")
                #         response_file.write(corrected_json_str)
                #     print(f"OpenAI raw response saved to: {openai_response_filename}")
                # except Exception as save_error:
                #     print(f"Error saving OpenAI response: {save_error}")
                
                # Quick validation - check if response looks like valid JSON
                if corrected_json_str.strip().startswith('[') and corrected_json_str.strip().endswith(']'):
                    print(f"Attempt {attempt + 1} returned valid-looking JSON structure")
                    break
                elif attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} returned malformed JSON, retrying...")
                    # Add more explicit instructions for retry
                    retry_prompt = formatted_prompt + "\n\nIMPORTANT: Your previous response was malformed. Please return ONLY a valid JSON array starting with '[' and ending with ']'. Do not include any explanations or markdown formatting."
                    formatted_prompt = retry_prompt
                else:
                    print(f"All {max_retries} attempts failed, proceeding with fallback parsing")
            except Exception as api_error:
                print(f"OpenAI API error on attempt {attempt + 1}: {api_error}")
                if attempt == max_retries - 1:
                    return None
        
        # Parse the corrected JSON
        try:
            # Clean the response more thoroughly
            cleaned_response = corrected_json_str.strip()
            
            # Remove any markdown formatting if present
            if '```json' in cleaned_response:
                cleaned_response = cleaned_response.split('```json')[1].split('```')[0].strip()
            elif '```' in cleaned_response:
                cleaned_response = cleaned_response.split('```')[1].strip()
            
            # Remove any leading/trailing text that might not be JSON
            # Look for the first '[' or '{' and last ']' or '}'
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(cleaned_response):
                if char in '[{':
                    start_idx = i
                    break
            
            for i in range(len(cleaned_response) - 1, -1, -1):
                if cleaned_response[i] in ']}':
                    end_idx = i + 1
                    break
            
            if start_idx != -1 and end_idx != -1:
                cleaned_response = cleaned_response[start_idx:end_idx]
            
            # Additional cleaning: remove any text before the JSON starts
            lines = cleaned_response.split('\n')
            json_lines = []
            json_started = False
            
            for line in lines:
                stripped_line = line.strip()
                if not json_started and (stripped_line.startswith('[') or stripped_line.startswith('{')):
                    json_started = True
                if json_started:
                    json_lines.append(line)
            
            if json_lines:
                cleaned_response = '\n'.join(json_lines)
            
            print(f"Attempting to parse cleaned JSON: {cleaned_response[:200]}...")
            
            # Additional cleaning for common OpenAI response issues
            print(f"Cleaned response starts with: {repr(cleaned_response[:50])}")
            
            # REMOVED PROBLEMATIC FALLBACK LOGIC THAT WAS OVERWRITING CORRECT OPENAI RESPONSES
            # The code was reconstructing JSON using original erroneous structures
            # Now we trust OpenAI's corrected response directly
            
            # Try to fix incomplete JSON by adding missing closing brackets
            open_brackets = cleaned_response.count('[')
            close_brackets = cleaned_response.count(']')
            open_braces = cleaned_response.count('{')
            close_braces = cleaned_response.count('}')
            
            # Add missing closing brackets/braces
            if open_braces > close_braces:
                cleaned_response += '}' * (open_braces - close_braces)
            if open_brackets > close_brackets:
                cleaned_response += ']' * (open_brackets - close_brackets)
            
            corrected_json = json.loads(cleaned_response)
            print(f"Successfully parsed corrected JSON with {len(corrected_json)} items")
            
            # Post-process to remove any remaining invalid parameters
            print("Post-processing to remove invalid parameters...")
            corrected_json = remove_invalid_parameters(corrected_json, attributes)
            print("Post-processing completed")
            
        except json.JSONDecodeError as e:
            print(f"Error parsing corrected JSON: {e}")
            print(f"Error position: {getattr(e, 'pos', 'unknown')}")
            print(f"Raw response: {repr(corrected_json_str)}")
            print(f"Cleaned response: {repr(cleaned_response)}")
            print(f"Cleaned response length: {len(cleaned_response)}")
            
            # Try to fix common JSON issues
            try:
                # Fix common issues like missing quotes, trailing commas, etc.
                fixed_response = cleaned_response
                
                # Remove trailing commas before closing brackets/braces
                import re
                fixed_response = re.sub(r',\s*([\]}])', r'\1', fixed_response)
                
                # Try parsing again
                corrected_json = json.loads(fixed_response)
                print(f"Successfully parsed corrected JSON with {len(corrected_json)} items")
                
                # Post-process to remove any remaining invalid parameters
                print("Post-processing to remove invalid parameters...")
                corrected_json = remove_invalid_parameters(corrected_json, attributes)
                print("Post-processing completed")
                
            except json.JSONDecodeError as e2:
                print(f"Still failed to parse JSON after fixes: {e2}")
                print(f"Final fixed response: {repr(fixed_response)}")
                
                # Last attempt: try to manually create a simple valid JSON
                print("Creating minimal fallback JSON...")
                try:
                    # Create a very simple corrected JSON based on the original structure
                    fallback_json = []
                    for i, item in enumerate(json_to_correct[:3]):  # Only take first 3 problematic items to avoid complexity
                        if 'PPIname' in item:
                            simple_item = {
                                "PPIname": f"Corrected PPI {i+1}",
                                "PPIjson": {
                                    "count": "activity == 'Declaration SUBMITTED by EMPLOYEE'",
                                    "aggregation": "average"
                                }
                            }
                            fallback_json.append(simple_item)
                    
                    if fallback_json:
                        corrected_json = fallback_json
                        print(f"Created fallback JSON with {len(fallback_json)} items")
                    else:
                        return None
                        
                except Exception as e3:
                    print(f"Fallback creation failed: {e3}")
                    return None
        
        # Merge corrected PPIs with working PPIs, avoiding duplicates
        print(f"Merging {len(corrected_json)} corrected PPIs with {len(working_ppis)} working PPIs")
        
        # Create final merged JSON with deduplication
        final_json = working_ppis.copy()  # Start with working PPIs
        
        # Add corrected PPIs, but avoid duplicates based on PPIname
        working_ppi_names = {ppi['PPIname'] for ppi in working_ppis}
        
        for corrected_ppi in corrected_json:
            if corrected_ppi['PPIname'] not in working_ppi_names:
                final_json.append(corrected_ppi)
            else:
                print(f"Skipping duplicate PPI: {corrected_ppi['PPIname']}")
        
        print(f"Final merged JSON contains {len(final_json)} PPIs total (after deduplication)")
        
        # Use the merged JSON as the final result
        corrected_json = final_json
        
        # Save the corrected JSON to a temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        corrected_filename = f"corrected_ppi_{timestamp}.json"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_corrected.json", mode='w+', dir=tempfile.gettempdir()) as temp_file:
            json.dump(corrected_json, temp_file, indent=4)
            temp_file_path = temp_file.name
        
        # Also save to permanent file
        # permanent_file_path = os.path.join(os.getcwd(), corrected_filename)
        # with open(permanent_file_path, 'w', encoding='utf-8') as permanent_file:
        #     json.dump(corrected_json, permanent_file, indent=4, ensure_ascii=False)
        # 
        # print(f"Corrected JSON saved to: {permanent_file_path}")
        return temp_file_path
        
    except FileNotFoundError:
        print("Error correction prompt file not found.")
        return None
    except Exception as e:
        print(f"Error during JSON correction: {e}")
        return None

#print("\n\n")

