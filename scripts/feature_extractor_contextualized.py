import torch
from transformers import BertTokenizer, BertModel


class BertExtractor:

    def __init__(self, bert_model, max_len, lower_case):
        """
        This class contains methods to extract contextualized word embeddings with a given Bert model.
        :param bert_model: which of the pretrained Bert model should be loaded.
        :param max_len: this pads the sentences to a maximum length such that computing the embeddings can be done for
        batches and is more efficient
        :param lower_case: whether to lower case or not
        """
        self._model = BertModel.from_pretrained(bert_model, output_hidden_states=True)
        self._model.eval()
        self._tokenizer = BertTokenizer.from_pretrained(bert_model, do_lower_case=lower_case)
        self._max_len = max_len

    def convert_sentence_to_indices(self, sentence):
        """

        :param sentence: A String representing a sentence, without special tokens
        :param max_len: an int : the length to which the sentence will be padded
        :return: A dictionary containing the following:
            input ids: list[int] (the word piece ids of the given sentence)
            token_type_ids: list[int] (the token type ids, in this case a list of 0, because we do not consider a
            pair of sequences
            attention_mask: list[int] (this list marks the real word pieces with 1 and the padded with 0)
        """
        return self.tokenizer.encode_plus(sentence, max_length=self.max_len, add_special_tokens=True,
                                          pad_to_max_length=True)

    def word_indices_in_sentence(self, sentence, target_word):
        """
        Given a sentence and a target word, this method returns the indices of the tokenized word within the sentence,
        when special tokens were added. So for the sentence "This is a sentence." we can assume that the Bert Tokenizer
        will tokenize it the following way: ['[CLS]', 'Th', '##is', 'is', 'a', 'sen', '##ten', '##ce', '.', '[SEP]]'
        Then for the target word 'sentence' we will retrieve a list with the corresponding indices - list([5, 6, 7])
        :param sentence: A String representing the sentence without special Tokens
        :param target_word: A String representing the target word
        :return: A list corresponding to the sequence of indices that match the target word in the given sentence
        """
        assert target_word in sentence, "target word must be contained in the context sentence!"
        sentence_indices = self.tokenizer.encode(sentence, add_special_tokens=True)
        word_indices = self.tokenizer.encode(target_word, add_special_tokens=False)
        all_word_indices = [sentence_indices.index(item) for item in word_indices]
        return all_word_indices

    @staticmethod
    def get_single_word_embedding(token_embeddings, target_word_indices):
        """
        For a list of token embeddings, extract the centroid of all word piece embeddings that belong to a target word.
        :param token_embeddings: A list of word piece embeddings that are part of a sentence.
        :param target_word_indices: A list of target word piece indices, that mark the indices of the target word in the
        list of token embeddings.
        :return: The centroid of the word piece embeddings (to do: other pooling options needed ? )
        """
        if len(target_word_indices) == 1:
            return token_embeddings[target_word_indices[0]]
        else:
            target_word_tokens = token_embeddings[
                                 target_word_indices[0]:target_word_indices[len(target_word_indices) - 1]]
            return target_word_tokens.sum(0) / target_word_tokens.shape[0]

    def convert_sentence_batch_to_indices(self, sentences):
        """
        Having a list of sentences as input this method returns the corresponding input_ids, token_type_ids and
        attention_masks for each sentence.
        :param sentences: a list of Strings.
        :return: three matrices, each vector corresponds to a certain type of id of a specific sentence
        """
        batch_input_ids = []
        batch_token_type_ids = []
        batch_attention_mask = []
        for sentence in sentences:
            converted = self.convert_sentence_to_indices(sentence=sentence)
            batch_input_ids.append(converted['input_ids'])
            batch_token_type_ids.append(converted['token_type_ids'])
            batch_attention_mask.append(converted['attention_mask'])
        return batch_input_ids, batch_token_type_ids, batch_attention_mask

    def get_bert_vectors(self, batch_input_ids, batch_attention_mask, batch_token_type_ids):
        """
        For a batch of input_ids, attention_masks, type_token_ids, Bert computes the corresponding layers for each token
        for each sentence in the batch.
        :param batch_input_ids:
        :param batch_attention_mask:
        :param batch_token_type_ids:
        :return: last_hidden_states: the top layer for each token within each sentence.
                 all_layers: all 12 layers for each token within each sentence.
        """
        with torch.no_grad():
            last_hidden_states, _, all_layers = self.model(input_ids=torch.tensor(batch_input_ids),
                                                           attention_mask=torch.tensor(batch_attention_mask),
                                                           token_type_ids=torch.tensor(batch_token_type_ids))
        return last_hidden_states, all_layers

    @staticmethod
    def get_mean_layer_pooling(layers, first_layer, last_layer):
        """
        Given a list of layers for a sentence, return one representation for the sentence by taking the mean of the
        specified layers.
        :param layers: The list of hidden states that is the output of Bert.
        :param first_layer: the first layer to include
        :param last_layer: the last layer to include
        :return: A torch tensor, representing the sentence vector (as the pooled mean of specified layers)
        """
        assert first_layer <= last_layer, "the lower layer must be lower than the upper layer"
        return torch.mean(torch.stack(layers[first_layer:last_layer]), dim=0)

    @staticmethod
    def get_mean_sentence_pooling(token_embeddings):
        return torch.mean(token_embeddings, dim=1)

    def get_single_word_representations(self, sentences, target_words):
        """
        Given a list of sentences and a list of target words as input, this method extracts a contextualized feature
        vector for the corresponding target word. A target word can consist of several word pieces, the embeddings for
        all word pieces are then averaged.
        :param sentences: A list of Strings (context sentences)
        :param target_words: a list of Strings (target words)
        :return:
        """
        assert len(sentences) == len(target_words), "for every sentence exactly one target word needs to be given."
        batch_input_ids, batch_token_type_ids, batch_attention_mask = self.convert_sentence_batch_to_indices(sentences)
        # shape last_hidden_states : batch_size x max_len x embedding_dim
        last_hidden_states, all_layers = self.get_bert_vectors(batch_input_ids, batch_token_type_ids,
                                                               batch_attention_mask)
        contextualized_embeddings = []
        for i in range(len(sentences)):
            target_word_indices = self.word_indices_in_sentence(sentences[i], target_words[i])
            token_embeddings = last_hidden_states[i]
            contextualized_emb = self.get_single_word_embedding(token_embeddings=token_embeddings,
                                                                target_word_indices=target_word_indices)
            contextualized_embeddings.append(contextualized_emb)
        return torch.stack(contextualized_embeddings)

    @property
    def model(self):
        return self._model

    @property
    def tokenizer(self):
        return self._tokenizer

    @property
    def max_len(self):
        return self._max_len
