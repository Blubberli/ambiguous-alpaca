import torch
from scripts import BasicTwoWordClassifier, TransweighTwoWordClassifier
from scripts.data_loader import SimplePhraseContextualizedDataset, SimplePhraseStaticDataset


def init_classifier(config):
    """
    This method initialized the classifier with parameter specified in the config file
    :param config: the configuration
    :return: a torch classifier
    """
    classifier = None
    if config["model"]["type"] == "basic_twoword":
        classifier = BasicTwoWordClassifier(input_dim=config["model"]["input_dim"],
                                            hidden_dim=config["model"]["hidden_size"],
                                            dropout_rate=config["model"]["dropout"],
                                            label_nr=config["model"]["label_size"])
    if config["model"]["type"] == "transweigh_twoword":
        classifier = TransweighTwoWordClassifier(input_dim=config["model"]["input_dim"],
                                                 hidden_dim=config["model"]["hidden_size"],
                                                 dropout_rate=config["model"]["dropout"],
                                                 label_nr=config["model"]["label_size"],
                                                 normalize_embeddings=config["model"]["normalize_embeddings"],
                                                 transformations=config["model"]["transformations"])
    assert classifier, "no valid classifier name specified in the configuration"
    return classifier


def get_datasets(config):
    """
    Returns the datasets with the corresponding features (defined in the config file)
    :param config: the configuration file
    :return: training, validation, test dataset
    """
    dataset_train = None
    dataset_test = None
    dataset_valid = None
    if config["feature_extractor"]["contextualized_embeddings"] is True:
        bert_parameter = config["feature_extractor"]["contextualized"]["bert"]
        bert_model = bert_parameter["model"]
        max_len = bert_parameter["max_sent_len"]
        lower_case = bert_parameter["lower_case"]
        batch_size = bert_parameter["batch_size"]
        if config["feature_extractor"]["context"] is False:
            dataset_train = SimplePhraseContextualizedDataset(data_path=config["train_data_path"],
                                                              bert_model=bert_model,
                                                              lower_case=lower_case, max_len=max_len,
                                                              batch_size=batch_size)
            dataset_valid = SimplePhraseContextualizedDataset(data_path=config["validation_data_path"],
                                                              bert_model=bert_model,
                                                              lower_case=lower_case, max_len=max_len,
                                                              batch_size=batch_size)
            dataset_test = SimplePhraseContextualizedDataset(data_path=config["test_data_path"],
                                                             bert_model=bert_model,
                                                             lower_case=lower_case, max_len=max_len,
                                                             batch_size=batch_size)
    else:
        dataset_train = SimplePhraseStaticDataset(data_path=config["train_data_path"],
                                                  embedding_path=config["feature_extractor"]["static"][
                                                      "pretrained_model"])
        dataset_test = SimplePhraseStaticDataset(data_path=config["test_data_path"],
                                                 embedding_path=config["feature_extractor"]["static"][
                                                     "pretrained_model"])
        dataset_valid = SimplePhraseStaticDataset(data_path=config["validation_data_path"],
                                                  embedding_path=config["feature_extractor"]["static"][
                                                      "pretrained_model"])
    assert dataset_test and dataset_valid and dataset_train, "there was an error when constructing the datasets"
    return dataset_train, dataset_valid, dataset_test


def convert_logits_to_binary_predictions(logits):
    """
    This method takse raw scores from a binary classifier and converts them into 0 and 1 respectively. The scores
    are expected to be unnormalized, a sigmoid is applied in this method
    :param logits: a list of class scores
    :return: a list of predictions (0 and 1)
    """
    predictions = torch.sigmoid(logits)
    predictions = [0 if x < 0.5 else 1 for x in predictions]
    return predictions