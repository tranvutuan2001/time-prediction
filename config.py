# General Config
log_to_use = 'credit'
algo_to_use = 'SVR_TS'

# Transition System Config
ts_window = 3  # positive int
ts_direction = 'backward'  # forward, backward
ts_view = 'sequence'  # sequence, set, multiset


def get_file_config():
    res = dict()
    if log_to_use == 'invoice':
        res['xes_path'] = './converted-invoice.xes'
        if algo_to_use == 'SVR':
            res['csv_path'] = './invoice.csv'
        else:
            res['csv_path'] = f'./invoice-svr-ts-{ts_view}-{ts_window}.csv'
    elif log_to_use == 'credit':
        res['xes_path'] = './converted-credit.xes'
        if algo_to_use == 'SVR':
            res['csv_path'] = './credit.csv'
        else:
            res['csv_path'] = f'./credit-svr-ts-{ts_view}-{ts_window}.csv'
    return res


def get_attributes_config():
    res = dict()
    res['category_columns'] = ['concept:name', 'lifecycle:transition', 'org:resource']
    res['descriptive_attributes'] = ['lifecycle:transition', 'concept:name', 'org:resource']
    res['target_attribute'] = 'remaining_time'
    res['end_activities'] = ['End']

    if algo_to_use == 'SVR_TS':
        res['descriptive_attributes'] = []
        res['category_columns'] = []
    if log_to_use == 'credit':
        res['end_activities'] = ['Requirements review']
    return res


category_columns: [str] = get_attributes_config()['category_columns']
descriptive_attributes: [str] = get_attributes_config()['descriptive_attributes']
target_attribute: str = get_attributes_config()['target_attribute']
end_activities = get_attributes_config()['end_activities']
csv_path = get_file_config()['csv_path']
xes_path = get_file_config()['xes_path']
