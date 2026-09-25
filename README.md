Your Other You

A music discovery app that creates two playlists: one based on your preferences and one for an alternate version of you. Answer questions about the music you enjoy, choose three favourite artists, and compare the results in the live Streamlit app:
  - https://genreapppy-bgt92zk2agbazrwyttmtua.streamlit.app/.
    
How it works
  1. Use sliders to describe your music preferences, including energy, danceability, tempo and other audio characteristics.
  2. Select three artists and choose how familiar you want the first playlist to feel.
  3. A trained CatBoost classifier predicts your top three genres from the slider answers.
  4. The app uses Last.fm to gather tracks from the predicted genres and your selected artists, then builds your personalised playlist.
  5. The app transforms your answers to create an opposing profile, predicts genres again, and generates your other you's playlist for comparison.

You can explore the playlists, discover artists and copy the track lists.

Dataset exploration and model choice

  - This repository includes two exploratory notebooks because I tested two datasets before choosing one for the finished app. The smaller dataset had around 250 tracks and five genres. A Random Forest model achieved approximately 72% accuracy, but the limited number of tracks and genres restricted the range of recommendations.
  - The larger dataset had more than 50,000 tracks and ten genres. Its initial CatBoost result was approximately 43% accuracy, which I improved to approximately 61% through further modelling. I chose this larger, ten-genre dataset for the final model because it covered a wider range of music, despite its lower accuracy. The smaller dataset and its notebook remain in the repository to show the exploration and the reasoning behind that decision; the app does not combine the two datasets.

The Kaggle sources explored were:

- Spotify Music Genre Classification: https://www.kaggle.com/code/shiyalkishan01/spotify-music-genre-classification
- Prediction of Music Genre: https://www.kaggle.com/datasets/vicsuperman/prediction-of-music-genre
The first link is a Kaggle notebook page and the second is a dataset page. See the exploratory notebooks in this repository for the corresponding data preparation and experiments.

Tools and technologies

  - Python, Pandas, scikit-learn, CatBoost, Streamlit and the Last.fm API.
    
Limitations

  - Genre predictions are estimates based on the available training data and slider inputs. Last.fm supplies track candidates, so the generated playlists also depend on the tracks returned by its API. The alternate playlist is a creative contrast to your inputs rather than an objective measure of opposite musical taste.
    
Try it
  - https://genreapppy-bgt92zk2agbazrwyttmtua.streamlit.app/

    
