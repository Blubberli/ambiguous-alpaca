import unittest
import math
import pathlib
import numpy as np
import torch
from torch import optim
from utils import loss_functions
import torch.nn.functional as F
from ranking_models import FullAdditiveJointRanker
from utils.data_loader import StaticRankingDataset, MultiRankingDataset
from torch.utils.data import DataLoader


class JointFullAdditiveRanking(unittest.TestCase):
    """
    this class tests the joint matrix model
    This test suite can be ran with:
        python -m unittest -q tests.JointRankingTest
    """

    def setUp(self):
        self._data_path_1 = pathlib.Path(__file__).parent.absolute().joinpath("/Users/ehuber/Documents/ambiguous_alpaca/ambigous-alpaca/Data/test_data_for_ranking_tests/test.txt")
        self._data_path_2 = pathlib.Path(__file__).parent.absolute().joinpath("/Users/ehuber/Documents/ambiguous_alpaca/ambigous-alpaca/Data/test_data_for_ranking_tests/val.txt")
        self._embedding_path = str(pathlib.Path(__file__).parent.absolute().joinpath(
            "embeddings/german-skipgram-mincount-30-ctx-10-dims-300.fifu"))
        self._dataset_1 = StaticRankingDataset(self._data_path_1, self._embedding_path, head="head",
                                               mod="modifier", phrase="label", separator=" ")
        self._dataset_2 = StaticRankingDataset(self._data_path_2, self._embedding_path, head="head",
                                               mod="modifier", phrase="label", separator=" ")
        modifier_embeddings = F.normalize(torch.rand((50, 100)), dim=1)
        head_embeddings = F.normalize(torch.rand((50, 100)), dim=1)
        gold_composed = F.normalize(torch.rand((50, 100)), dim=1)
        device = torch.device("cpu")
        self.input_1 = {"w1": modifier_embeddings, "w2": head_embeddings, "l": gold_composed, "device": device}
        self.input_2 = {"w1": modifier_embeddings, "w2": head_embeddings, "l": gold_composed, "device": device}
        self.model = FullAdditiveJointRanker(input_dim=100, dropout_rate=0.0, normalize_embeddings=True)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.1)

    @staticmethod
    def access_named_parameter(model, parameter_name):
        for name, param in model.named_parameters():
            if param.requires_grad:
                if name == parameter_name:
                    return param.clone()


    def test_model_loss(self):
        self.optimizer.zero_grad()
        composed, rep_1, rep_2 = self.model(self.input_1)
        loss_1 = loss_functions.get_loss_cosine_distance(original_phrase=self.input_1["l"], composed_phrase=rep_1,
                                                         dim=1, normalize=False).item()
        composed, rep_1, rep_2 = self.model(self.input_2)
        loss_2 = loss_functions.get_loss_cosine_distance(original_phrase=self.input_1["l"], composed_phrase=rep_2,
                                                         dim=1, normalize=False).item()
        np.testing.assert_equal(math.isnan(loss_1), False)
        np.testing.assert_equal(math.isnan(loss_2), False)

        np.testing.assert_equal(loss_1 >= 0, True)
        np.testing.assert_equal(loss_2 >= 0, True)




    def test_parameter_updated_with_training(self):
        adj_1_before_training = self.access_named_parameter(self.model, "_adj_matrix_1")
        adj_2_before_training = self.access_named_parameter(self.model, "_adj_matrix_2")
        noun_1_before_training = self.access_named_parameter(self.model, "_noun_matrix_1")
        noun_2_before_training = self.access_named_parameter(self.model, "_noun_matrix_2")

        general_adj_weights_before_training = self.access_named_parameter(self.model, "_general_adj_matrix.weight")
        general_noun_weights_before_training = self.access_named_parameter(self.model, "_general_noun_matrix.weight")

        for epoch in range(0,5):
            self.optimizer.zero_grad()
            composed, rep_1, rep_2 = self.model(self.input_1)
            loss_1 = loss_functions.get_loss_cosine_distance(original_phrase=self.input_1["l"], composed_phrase=rep_1,
                                                             dim=1, normalize=False)
            composed, rep_1, rep_2 = self.model(self.input_2)
            loss_2 = loss_functions.get_loss_cosine_distance(original_phrase=self.input_1["l"], composed_phrase=rep_2,
                                                             dim=1, normalize=False)
            loss = loss_1 + loss_2
            loss.backward()
            self.optimizer.step()
            adj_1_after_training = self.access_named_parameter(self.model, "_adj_matrix_1")
            adj_2_after_training = self.access_named_parameter(self.model, "_adj_matrix_2")
            noun_1_after_training = self.access_named_parameter(self.model, "_noun_matrix_1")
            noun_2_after_training = self.access_named_parameter(self.model, "_noun_matrix_2")
            general_adj_weights_after_training = self.access_named_parameter(self.model, "_general_adj_matrix.weight")
            general_noun_weights_after_training = self.access_named_parameter(self.model,
                                                                               "_general_noun_matrix.weight")
            
        difference_adj1_layer = torch.sum(
            adj_1_before_training - adj_1_after_training ).item()
        difference_adj2_layer = torch.sum(
            adj_2_before_training - adj_2_after_training).item()
        difference_noun1_layer = torch.sum(
            noun_1_before_training- noun_1_after_training).item()
        difference_noun2_layer = torch.sum(noun_2_before_training - noun_2_after_training).item()

        difference_general_adj = torch.sum(general_adj_weights_before_training - general_adj_weights_after_training).item()
        difference_general_noun = torch.sum(general_noun_weights_before_training - general_noun_weights_after_training).item()

        np.testing.assert_equal(difference_adj1_layer != 0.0, True)
        np.testing.assert_equal(difference_adj2_layer != 0.0, True)
        np.testing.assert_equal(difference_noun1_layer != 0.0, True)
        np.testing.assert_equal(difference_noun2_layer != 0.0, True)
        np.testing.assert_equal(difference_general_adj != 0.0, True)
        np.testing.assert_equal(difference_general_noun != 0.0, True)


    def test_output_shape(self):
        expected_shape = np.array([50, 100])
        composed_phrase, rep_1, rep_2 = self.model(self.input_2)
        np.testing.assert_almost_equal(composed_phrase.shape, expected_shape)
        np.testing.assert_almost_equal(rep_1.shape, expected_shape)
        np.testing.assert_almost_equal(rep_2.shape, expected_shape)

    def test_embedding_normalization(self):
        """Test whether the composed phrase has been normalized to unit norm"""
        composed_phrase, rep_1, rep_2 = self.model(self.input_2)
        np.testing.assert_almost_equal(np.linalg.norm(composed_phrase[0].data), 1.0)
        np.testing.assert_almost_equal(np.linalg.norm(rep_1[0].data), 1.0)
        np.testing.assert_almost_equal(np.linalg.norm(rep_2[0].data), 1.0)
