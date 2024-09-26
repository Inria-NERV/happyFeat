
import ruamel.yaml

## Change the Extraction yaml file  
def modify_extraction_yaml_new(yaml_file, filename=None, rate=None, keys=None, epoch_params=None, trim_samples=None,
                           welch_rate=None, recorder_filename=None, path=None,nfft=None):
    print("---Modifying " + yaml_file + " parameters")

    # Read the YAML file
    yaml = ruamel.yaml.YAML()
    with open(yaml_file, 'r') as file:
        data = yaml.load(file)
    
    # Update the rate if provided
    if rate is not None:
        for graph in data.get('graphs', []):
            graph['rate'] = float(rate)
    
    # Update nodes based on their IDs and provided parameters
    for graph in data.get('graphs', []):
        if graph['id'] == 'analysing':
            for node in graph.get('nodes', []):
                params = node.get('params', {})
                node_id = node['id']

                if node_id in ['select_A', 'select_B'] and keys is not None:
                    params['key'] = keys
                
                if node_id in ['epoching_A', 'epoching_B'] and epoch_params is not None:
                    params['before'] = float(epoch_params.get('before', params.get('before')))
                    params['after'] = float(epoch_params.get('after', params.get('after')))
                
                if node_id in ['trim_A', 'trim_B'] and trim_samples is not None:
                    params['samples'] = int(trim_samples)
                
                if node_id in ['welch_psd_A', 'welch_psd_B'] and welch_rate is not None:
                    params['rate'] = float(welch_rate)
                if node_id in ['welch_psd_A', 'welch_psd_B'] and nfft is not None:
                    params['nfft'] = int(nfft)
                
                if node_id == 'edf_reader' and filename is not None:
                    params['filename'] = filename  # Update filename for edf_reader node
                
                if node_id == 'Recorder' and recorder_filename is not None:
                    params['filename'] = recorder_filename
                    params['path'] = path
    
    # Write the updated YAML back to the file
    with open(yaml_file, 'w') as file:
        yaml.dump(data, file)
    
## Change the Extraction yaml file 
def modify_Edf_Reader_yaml(yaml_file, new_filename):
    print("---Modifying filename in " + yaml_file)

    yaml = ruamel.yaml.YAML()

    # Read the YAML file
    with open(yaml_file, 'r') as file:
        data = yaml.load(file)

    # Update the filename in the edf_reader node
    for graph in data.get('graphs', []):
        for node in graph.get('nodes', []):
            if node['id'] == 'edf_reader':
                node['params']['filename'] = new_filename

    # Write the updated YAML back to the file
    with open(yaml_file, 'w') as file:
        yaml.dump(data, file)

    return


def update_filenames(yaml_file, new_filenames_A, new_filenames_B, new_selections,path,attemptId,cv=None):
    """
    Update the filenames for the 'data_reader_A' and 'data_reader_B' nodes,
    and the selections for the 'select_A' and 'select_B' nodes in the graph.

    Parameters:
    - yaml_file: str
        The path to the YAML file.
    - new_filenames_A: list of str
        The new filenames for the 'data_reader_A' node.
    - new_filenames_B: list of str
        The new filenames for the 'data_reader_B' node.
    - new_selections_A: list of list
        The new selections for the 'select_A' node.
    - new_selections_B: list of list
        The new selections for the 'select_B' node.
    """
    yaml = ruamel.yaml.YAML()

    # Read the YAML file
    with open(yaml_file, 'r') as file:
        data = yaml.load(file)

    # Update the parameters in the nodes
    for graph in data.get('graphs', []):
        for node in graph.get('nodes', []):
            if node['id'] == 'data_reader_A':
                node['params']['filenames'] = new_filenames_A
            elif node['id'] == 'data_reader_B':
                node['params']['filenames'] = new_filenames_B
            elif node['id'] == 'select_A':
                node['params']['selections'] = new_selections
            elif node['id'] == 'select_B':
                node['params']['selections'] = new_selections
            elif node['id']=='ML_LDA':
                node['params']['path']=path
                node['params']['filename']=str(attemptId)
            elif node['id']=='ML_LDA' and cv is not None:
                node['params']['cv']= cv


    # Write the updated data back to the YAML file
    with open(yaml_file, 'w') as file:
        yaml.dump(data, file)