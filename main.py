import pandas as pd
from pm4py.objects.log.importer.xes import importer as xes_importer
from preprocess import build_incomplete_dataframe
from pm4py.objects.log import obj as log_instance
from training import train_and_test
import config
import os.path

category_columns: [str] = config.category_columns
csv_path = config.csv_path
xes_path = config.xes_path

df = None
if os.path.isfile(csv_path):
    df = pd.read_csv(csv_path)
else:
    complete_event_log: log_instance.EventLog = xes_importer.apply(xes_path)
    df = build_incomplete_dataframe(complete_event_log)
    df.to_csv(csv_path, index=False)

train_and_test(df)
