import yaml

import ruamel.yaml

def modify_extraction_yaml(yaml_file, rate=None, keys=None, epoch_params=None, trim_samples=None,
                           welch_rate=None, band_ranges=None, recorder_filename=None, path=None):
    print("---Modifying " + yaml_file + " parameters")

    # Read the YAML file
    yaml = ruamel.yaml.YAML()
    with open(yaml_file, 'r') as file:
        data = yaml.load(file)
    
    # Update the rate if provided
    if rate is not None:
        for graph in data.get('graphs', []):
            graph['rate'] = rate
    
    # Update nodes based on their IDs and provided parameters
    for graph in data.get('graphs', []):
        if graph['id'] == 'analysing':
            for node in graph.get('nodes', []):
                params = node.get('params', {})
                node_id = node['id']

                
                if node_id in ['select_A', 'select_B'] and keys is not None:
                    params['key'] = keys
                
                if node_id in ['epoching_A', 'epoching_B'] and epoch_params is not None:
                    params['before'] = epoch_params.get('before', params.get('before'))
                    params['after'] = epoch_params.get('after', params.get('after'))
                
                if node_id in ['trim_A', 'trim_B'] and trim_samples is not None:
                    params['samples'] = trim_samples
                
                if node_id in ['welch_psd_A', 'welch_psd_B'] and welch_rate is not None:
                    params['rate'] = welch_rate
                
                if node_id == 'Bands_A' and band_ranges is not None and 'range_A' in band_ranges:
                    params['bands'] = {'range_A': band_ranges['range_A']}
                
                if node_id == 'Bands_B' and band_ranges is not None and 'range_B' in band_ranges:
                    params['bands'] = {'range_B': band_ranges['range_B']}
        
        if graph['id'] == 'saving':
            for node in graph.get('nodes', []):
                params = node.get('params', {})
                node_id = node['id']
                
                if node_id == 'Recorder' and recorder_filename is not None:
                    params['filename'] = recorder_filename
                    params['path'] = path
    
    # Write the updated YAML back to the file
    with open(yaml_file, 'w') as file:
        yaml.dump(data, file)
    print("done")
# Example usage:
# modify_extraction_yaml('path_to_your_yaml_file.yaml', rate=2, keys=['CP5', 'CP1'], epoch_params={'before': 1, 'after': 4})


def modify_Edf_Reader_yaml(yaml_file, new_filename):
    print("---Modifying filename in " + yaml_file)

    # Read the YAML file
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)
    # Update the filename in the edf_reader node
    for graph in data.get('graphs', []):
        for node in graph.get('nodes', []):
            if node['id'] == 'edf_reader':
                node['params']['filename'] = new_filename
    
    # Write the updated YAML back to the file
    with open(yaml_file, 'w') as file:
        yaml.safe_dump(data, file)

    return