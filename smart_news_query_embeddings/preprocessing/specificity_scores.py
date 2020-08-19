"""
Copyright 2020 Google LLC.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import spacy
import pandas as pd
import numpy as np
import en_core_web_sm
from tqdm import tqdm
nlp = en_core_web_sm.load()

def get_token_list(sentences):

    """
    Tokenizes the given list of sentences
    by extracting the relevant named entities
    from each sentence. This is a key part of the
    specificity score algorithm.
    """

    token_lists = []
    tokens = []
    types = []
    for s in tqdm(sentences):
        doc = nlp(s)
        token_list = []
        for X in doc.ents:
            token, label = X.text, X.label_
            token_list.append((token, label))
            tokens.append(token)
            types.append(label)
        token_lists.append(token_list)
    token_df = pd.DataFrame({
            'token': tokens,
            'type': types
    })
    return token_df, token_lists

def get_token_scores(token_df):

    """
    From a DataFrame of tokens and their types, generate the score
    for each token based on its own count and the average of all token
    counts for its entity type. See design doc for more details.

    Arguments:
        token_df: A DataFrame with columns 'token' for the string value of the token
        and 'type' for the entity type of the token.
    Returns:
        A DataFrame indexed by (token, type) tuples and a 'score' column containing the
        specifcity score of that (token, type) tuple.
    """

    token_df['count'] = 1
    by_type_and_token = token_df.groupby(['type', 'token']).count()
    average_by_type = by_type_and_token.reset_index().groupby('type').agg({
        'count': 'mean'
    })
    mean_by_type = average_by_type.rename({'count': 'mean_count'}, axis=1).reset_index()
    token_scores = by_type_and_token.reset_index().merge(mean_by_type, how='outer')
    token_scores['score'] = np.log(token_scores['count'] / token_scores['mean_count'])
    indexed_token_scores = token_scores.set_index(['type', 'token'])
    return indexed_token_scores

def get_normalized_scores(token_lists, indexed_token_scores):
    scores = []
    for token_list in tqdm(token_lists):
        s = 0
        for t in token_list:
            name, label = t
            s += indexed_token_scores.loc[label, name]['score']
        s /= len(token_list) if len(token_list) > 0 else np.nan
        scores.append(s)
    return pd.Series(scores)

def get_specificity_scores(sentences):
    token_df, token_lists = get_token_list(sentences)
    indexed_token_scores = get_token_scores(token_df)
    return get_normalized_scores(token_lists, indexed_token_scores)