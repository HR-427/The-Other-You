#----- FILE PURPOSE -----

'''
    This file will: Load the model and preprocessing files, 
    arrange the song features, fill any missing values, 
    predict probabilities for all ten genres, average the 
    results across the user's songs, and return the top 
    three genres as percentages (three most likely genres
    user listens to). 
'''



#----- IMPORTS -----

import joblib 
import numpy as np
import pandas as pd 

from catboost import CatBoostClassifier 

MODEL_PATH = "expanded_genre_model.cbm"
MODEL_INFORMATION_PATH = "genre_model_information.pkl"



#----- FUNCTIONS -----

def load_genre_model(): 
    # load trained catboost model and preprocessing information 

    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)

    model_information = joblib.load(
        MODEL_INFORMATION_PATH
    )

    return model, model_information

genre_model, model_information = load_genre_model() 




def prepare_song_features(song_records): 
    # convert song information to format expected by moodel
    # song_records is list of dictionaries, one dictionary = one song 

    song_features = pd.DataFrame(song_records)
    

    numerical_features = model_information[
        "numerical_features"
    ]

    categorical_features = model_information[
        "categorical_features"
    ]

    feature_columns = model_information[
        "feature_columns"
    ]

    training_medians = model_information[
        "training_medians"
    ]


    # add any missing model columns 
    for column in feature_columns: 
        if column not in song_features.columns: 
            song_features[column] = np.nan


    # convert numerical features to numbers 
    for column in numerical_features: 
        song_features[column] = pd.to_numeric(
            song_features[column], 
            errors = "coerce"
        )

        song_features[column] = song_features[column].fillna(
            training_medians[column]
        )

    # prepare categorical features for catboost
    for column in categorical_features:
        song_features[column] = (
            song_features[column]
            .fillna("Unknown")
            .astype(str)
        )

    # ensure the columns are in the original training order 
    return song_features[feature_columns]




def predict_top_genres(song_records, top_n=3):
    # predict the user's overall top genres from their selected songs.


    song_features = prepare_song_features(song_records)

    # get genre probabilities for each song
    song_probabilities = genre_model.predict_proba(
        song_features
    )

    # average probabilities across all selected songs
    average_probabilities = song_probabilities.mean(axis=0)

    genre_names = np.asarray(
        model_information["genre_classes"]
    )

    # find the genres with the highest probabilities
    top_indices = np.argsort(
        average_probabilities
    )[-top_n:][::-1]

    results = pd.DataFrame({
        "Genre": genre_names[top_indices],
        "Probability": average_probabilities[top_indices]
    })

    # convert probabilities into percentages
    results["Probability"] = (
        results["Probability"] * 100
    ).round(1)

    return results