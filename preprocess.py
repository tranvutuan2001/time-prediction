from pm4py.objects.log import obj as log_instance
from datetime import timedelta
import pandas as pd
import config
from pm4py.objects.transition_system.obj import TransitionSystem
from pm4py.algo.discovery.transition_system import algorithm as ts_algo
from pm4py.algo.discovery.transition_system.variants import view_based as ts_view_based


def build_incomplete_dataframe(complete_event_log: log_instance.EventLog):
    algo_to_use = config.algo_to_use

    # Create incomplete traces
    data: [(log_instance.Trace, timedelta)] = []
    for complete_trace in complete_event_log:
        for incomplete_trace, remaining_time in one_complete_trace_to_many_incomplete_traces(complete_trace):
            data.append((incomplete_trace, remaining_time))

    # Convert traces to dataframe
    if algo_to_use == 'SVR':
        return convert_data_to_dataframe(data)
    else:
        states = get_all_states_in_transition_system(complete_event_log)
        return convert_data_to_dataframe_SVR_TS(data, states)


def one_complete_trace_to_many_incomplete_traces(complete_trace: log_instance.Trace) -> [log_instance.Trace]:
    end_activities = config.end_activities
    remove_incomplete = config.remove_in_complete
    require_complete = config.require_complete
    trace_name: str = complete_trace.attributes['concept:name']
    res = []
    last_activity = complete_trace[-1]
    is_last_activity_completed = True

    if 'lifecycle:transition' in last_activity:
        is_last_activity_completed = last_activity['lifecycle:transition'] == 'complete'

    if (last_activity['concept:name'] not in end_activities and remove_incomplete) or (require_complete and not is_last_activity_completed):
        return res

    for i, current_activity in enumerate(complete_trace):
        if i == 0:
            continue
        end_time_stamp = last_activity['time:timestamp']
        remaining_time = end_time_stamp - current_activity['time:timestamp']
        res.append((
            log_instance.Trace(complete_trace[0:i+1], attributes={'concept:name': trace_name + '-tuan-' + str(i)}),
            remaining_time
        ))
    return res


def trace_to_row_SVR(trace: log_instance.Trace) -> dict:
    descriptive_attributes: [str] = config.descriptive_attributes

    row = dict()
    for attribute in descriptive_attributes:
        for index, event in enumerate(reversed(trace)):
            if attribute in event:
                row[attribute] = event[attribute]
                break
            if index == len(trace) - 1:
                row[attribute] = None
    return row


def jaccard_similarity_set(set_a: set, set_b: set):
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return len(intersection) / len(union)


def jaccard_similarity_multiset(bag_a: dict, bag_b: dict):
    total_element = 0
    intersection = 0
    for key_a in bag_a:
        total_element += bag_a[key_a]
    for key_b in bag_b:
        total_element += bag_b[key_b]

    for key_a in bag_a:
        for key_b in bag_b:
            if key_a == key_b:
                intersection += min(bag_a[key_a], bag_b[key_b])
    return intersection / total_element


def levenshtein(s1: [str], s2: [str]):
    l1 = len(s1)
    l2 = len(s2)
    matrix = [list(range(l1 + 1))] * (l2 + 1)
    for zz in list(range(l2 + 1)):
        matrix[zz] = list(range(zz, zz + l1 + 1))
    for zz in list(range(0, l2)):
        for sz in list(range(0, l1)):
            if s1[sz] == s2[zz]:
                matrix[zz + 1][sz + 1] = min(matrix[zz + 1][sz] + 1, matrix[zz][sz + 1] + 1, matrix[zz][sz])
            else:
                matrix[zz + 1][sz + 1] = min(matrix[zz + 1][sz] + 1, matrix[zz][sz + 1] + 1, matrix[zz][sz] + 1)
    distance = float(matrix[l2][l1])
    result = 1.0 - distance / max(l1, l2)
    return result


def trace_to_row_SVR_TS(trace: log_instance.Trace, states: [set]) -> dict:
    view = config.ts_view
    row = dict()
    if view == 'set':
        current_state = get_current_state_set(trace)
        for i, state in enumerate(states):
            sim = jaccard_similarity_set(current_state, state)
            row[f'{i}-{"-".join(state)}'] = sim
    elif view == 'multiset':
        current_state = get_current_state_multiset(trace)
        for i, state in enumerate(states):
            sim = jaccard_similarity_multiset(current_state, state)
            row[f'{i}-{"-".join(state)}'] = sim
    else:
        current_state = get_current_state_sequence(trace)
        for i, state in enumerate(states):
            sim = levenshtein(current_state, state)
            row[f'{i}-{"-".join(state)}'] = sim
    return row


def get_current_state_set(trace: log_instance.Trace) -> []:
    window = config.ts_window
    trace_state = set()
    if len(trace) < window:
        for event in trace:
            trace_state.add(event['concept:name'])
    else:
        i = -1
        while window > 0:
            trace_state.add(trace[i]['concept:name'])
            i -= 1
            window -= 1
    return trace_state


def get_current_state_multiset(trace: log_instance.Trace) -> []:
    window = config.ts_window
    trace_state = dict()
    if len(trace) < window:
        for event in trace:
            if event['concept:name'] in trace_state:
                trace_state[event['concept:name']] += 1
            else:
                trace_state[event['concept:name']] = 1
    else:
        i = -1
        while window > 0:
            if trace[i]['concept:name'] in trace_state:
                trace_state[trace[i]['concept:name']] += 1
            else:
                trace_state[trace[i]['concept:name']] = 1
            i -= 1
            window -= 1
    return trace_state


def get_current_state_sequence(trace: log_instance.Trace) -> []:
    window = config.ts_window
    trace_state = []
    if len(trace) < window:
        for event in trace:
            trace_state.append(event['concept:name'])
    else:
        i = -1
        while window > 0:
            trace_state.append(trace[i]['concept:name'])
            i -= 1
            window -= 1
    return trace_state


def convert_data_to_dataframe(data: [(log_instance.Trace, timedelta)]):
    descriptive_attributes: [str] = config.descriptive_attributes
    target_attribute: str = config.target_attribute
    res = dict()

    # Init empty dict with descriptive attributes as keys. Value of each key is []
    for attribute in descriptive_attributes:
        res[attribute] = []
    res[target_attribute] = []

    for data_row in data:
        x = trace_to_row_SVR(data_row[0])
        y = data_row[1]
        for attribute in descriptive_attributes:
            res[attribute].append(x[attribute])
        res[target_attribute].append(y)

    return pd.DataFrame.from_dict(res)


def convert_data_to_dataframe_SVR_TS(data: [(log_instance.Trace, timedelta)], states: [set]):
    res = dict()
    target_attribute: str = config.target_attribute

    for i, state in enumerate(states):
        res[f'{i}-{"-".join(state)}'] = []
    res[target_attribute] = []

    for incomplete_trace, remaining_time in data:
        x = trace_to_row_SVR_TS(incomplete_trace, states)
        y = remaining_time
        for i, state in enumerate(states):
            res[f'{i}-{"-".join(state)}'].append(x[f'{i}-{"-".join(state)}'])
        res[target_attribute].append(y)
    return pd.DataFrame.from_dict(res)


def get_all_states_in_transition_system(complete_event_log: log_instance.EventLog) -> []:
    ts: TransitionSystem = ts_algo.apply(complete_event_log,
                                         {ts_view_based.Parameters.PARAM_KEY_VIEW: config.ts_view,
                                          ts_view_based.Parameters.PARAM_KEY_WINDOW: config.ts_window,
                                          ts_view_based.Parameters.PARAM_KEY_DIRECTION: config.ts_direction})

    states = []
    for state in ts.states:
        if len(state.incoming) != 0:
            states.append(state.name)
    return states
