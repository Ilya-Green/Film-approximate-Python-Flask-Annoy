from flask import Flask, jsonify, request, render_template
import pandas as pd
import gensim
from gensim.models import Doc2Vec
from annoy import AnnoyIndex

import spacy

nlp = spacy.load("en_core_web_sm")
# from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)

# app = WsgiToAsgi(app)
# Load movie data and create Annoy index
movies_df = pd.read_csv('movies.csv')
tagged_movies = [gensim.models.doc2vec.TaggedDocument(title.split(), [i]) for i, title in enumerate(movies_df['Title'])]

model = Doc2Vec.load('doc2vec.model')

# Load Doc2Vec model
doc2vec_model = gensim.models.Doc2Vec.load('doc2vec.model')

# Create AnnoyIndex object
movie_vectors = [doc2vec_model.infer_vector(title.split()) for title in movies_df['Title']]
annoy_index = AnnoyIndex(doc2vec_model.vector_size, metric='angular')
for i in range(len(movie_vectors)):
    annoy_index.add_item(i, movie_vectors[i])
annoy_index.build(50)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/searchbycategory')
def sbc():
    return render_template('search_by_category.html')

@app.route('/suggest')
def suggest():
  query = request.args.get('q')
  suggestions = movies_df[movies_df['Title'].str.contains(query, case=False, regex=False)]['Title'].tolist()
  return jsonify(suggestions)

@app.route('/search')
def search():
    #извлекает параметр 'query' из GET-запроса (если он был передан), который содержит поисковой запрос, и присваивает его переменной query.
    query = request.args.get('query')
    #если query отсутствует или имеет пустое значение, возвращает сообщение об ошибке в формате JSON.
    if not query:
        return jsonify({'error': 'query parameter is missing'})
    #используя модель Doc2Vec, получает вектор запроса movie_vector, преобразовав текст запроса query в список слов и вызвав метод infer_vector
    movie_vector = doc2vec_model.infer_vector(query.split())
    #используя библиотеку ANNOY, находит 10 ближайших соседей для вектора movie_vector в индексе annoy_index. Параметр include_distances=True запрашивает возвращение расстояний до каждого соседа, которые присваиваются переменной distances.
    nearest_neighbors, distances = annoy_index.get_nns_by_vector(movie_vector, 5, search_k=500, include_distances=True)
    #используя пандас, извлекает из датафрейма movies_df названия и постеры 10 фильмов, соответствующих ближайшим соседям, и присваивает их переменной 
    similar_movies = movies_df.iloc[nearest_neighbors][['Title', 'Poster']]
    #добавляет новый столбец Distance в similar_movies и присваивает ему значения расстояний distances.
    similar_movies['Distance'] = distances
    # определение градации цвета в зависимости от расстояния
    colors = []
    for distance in distances:
        if distance < 0.2:
            colors.append('green')
        elif distance < 0.4:
            colors.append('yellow')
        elif distance < 0.6:
            colors.append('orange')
        else:
            colors.append('red')
    similar_movies['Color'] = colors
    #преобразует датафрейм similar_movies в формат JSON, используя метод to_dict, и возвращает результат поиска в формате JSON.
    return jsonify(similar_movies.to_dict(orient='records'))




@app.route('/search_by_category')
def search_by_category():
    genre = request.args.get('genre')
    year = request.args.get('year')
    rating = request.args.get('rating')
    
    query = f"{genre} {year} {rating}"
    
    movie_vector = doc2vec_model.infer_vector(query.split())
    nearest_neighbors = annoy_index.get_nns_by_vector(movie_vector, 10)
    similar_movies = movies_df.iloc[nearest_neighbors]['Title']
    
    return render_template('search_by_category.html', similar_movies=similar_movies.tolist())




if __name__ == '__main__':
    app.run(debug=True)

