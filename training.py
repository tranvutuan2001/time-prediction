import math

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import cross_validate
import config


def train_and_test(df: pd.DataFrame):
    descriptive_attributes: [str] = config.descriptive_attributes
    target_attribute: str = config.target_attribute
    category_columns = config.category_columns
    if category_columns is None:
        category_columns = []
    x_train, x_test, y_train, y_test = prepare_df(df, descriptive_attributes, target_attribute, category_columns)
    C, epsilon = fine_tune(SVR, x_train, y_train, [1, 50, 100, 500], [0.2, 1, 10, 20])
    predictor = train(SVR, x_train, y_train, C, epsilon)
    print(test(predictor, x_test, y_test))
    print(f'C: {C}; epsilon: {epsilon}')


def fine_tune(algo, x_train, y_train, C_list, episilon_list) -> {(int, int)}:
    best_C = C_list[0]
    best_epsilon = episilon_list[0]
    best_score = -1
    for C in C_list:
        for episilon in episilon_list:
            current_score = 0
            cv = 3
            cv_results = cross_validate(algo(C=C, epsilon=episilon), x_train, y_train, cv=cv, scoring='neg_mean_absolute_percentage_error')
            for score in cv_results['test_score']:
                current_score += score * (-1)
            current_score /= cv
            if current_score < best_score or best_score == -1:
                best_C = C
                best_epsilon = episilon
                best_score = current_score
    return best_C, best_epsilon


def prepare_df(df: pd.DataFrame, descriptive_attributes: [str], target_attribute: str, category_columns: [str] = None):
    if category_columns is None:
        category_columns = []
    df.dropna(inplace=True)
    df[target_attribute] = pd.to_timedelta(df[target_attribute]).dt.seconds
    df = df.drop(df[df[target_attribute] < 100].index)
    df = df.sample(frac=0.05, random_state=42)
    y = df[target_attribute]
    if len(descriptive_attributes) == 0:
        x = pd.get_dummies(df, columns=category_columns, drop_first=True)
    else:
        x = pd.get_dummies(df[descriptive_attributes], columns=category_columns, drop_first=True)
    return train_test_split(x, y, test_size=0.2, random_state=42)


def train(algo, x_train: pd.DataFrame, y_train: pd.Series, C, epsilon) -> Pipeline:
    predictor = make_pipeline(StandardScaler(), algo(C=C, epsilon=epsilon))
    predictor.fit(x_train, y_train)
    return predictor


def test(predictor: Pipeline, x_test: pd.DataFrame, y_test: pd.Series):
    y_pred = predictor.predict(x_test)
    y_test = y_test.to_numpy()
    return [mean_absolute_percentage_error(y_test, y_pred), root_mean_square_error(y_test, y_pred)]


def root_mean_square_error(y_test, y_pred):
    n = len(y_test)
    sum = 0
    for i in range(len(y_test)):
        e = math.pow((y_test[i] - y_pred[i]) / y_test[i], 2)
        sum += e
    sq = math.sqrt(sum / n)
    return sq
