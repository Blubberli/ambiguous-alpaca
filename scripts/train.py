from scripts.composition_functions import transweigh, transweigh_weight, tw_transform, concat
from scripts.basic_twoword_classifier import BasicTwoWordClassifier
from scripts.feature_extractor_contextualized import BertExtractor
from scripts.loss_functions import multi_class_cross_entropy, binary_class_cross_entropy
import torch
import numpy as np


def main():
    batch_wordone = torch.from_numpy(
            np.array([[5.0, 2.0, 3.0], [0.0, 3.0, 1.0], [1.0, 0.0, 6.0]], dtype="float32"))
    batch_wordtwo = torch.from_numpy(
            np.array([[1.0, 1.0, 1.0], [1.0, 2.0, 1.0], [2.0, 2.0, 2.0]],dtype="float32"))
    target = torch.from_numpy(
            np.array([0,1,2],dtype="int64"))

    for epoch in range(10):
        classifier = BasicTwoWordClassifier(input_dim=batch_wordtwo.shape[1]*2, hidden_dim=batch_wordone.shape[0], label_nr=len(target))
        out = classifier(batch_wordone, batch_wordtwo)
        loss = multi_class_cross_entropy(out, target)
        loss.backward()
        print(loss)

if __name__ == "__main__":
    main()