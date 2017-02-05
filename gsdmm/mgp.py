from numpy.random import multinomial
from numpy import log, exp, float64
import numpy as np
from collections import defaultdict

class MovieGroupProcess:
    def __init__(self, K=8, alpha=0.1, beta=0.1, n_iters=30):
        '''
        A MovieGroupProcess is a conceptual model introduced by Yin and Wang 2014 to
        describe their Gibbs sampling algorithm for a Dirichlet Mixture Model for the
        clustering short text documents

        Imagine a professor is leading a film class. At the start of the class, the students
        are randomly assigned to K tables. Before class begins, the students make lists of
        their favorite films. The teacher reads the role n_iters times. When
        a student is called, the student must select a new table satisfying either:
            1) The new table has more students than the current table.
        OR
            2) The new table has students with similar lists of favorite movies.

        :param K: int
            Upper bound on the number of possible clusters. Typically many fewer
        :param alpha: float between 0 and 1
            Alpha controls the probability that a student will join a table that is currently empty
            When alpha is 0, no one will join an empty table.
        :param beta: float between 0 and 1
            Beta controls the student's affinity for other students with similar interests. A low beta means
            that students desire to sit with students of similar interests. A high beta means they are less
            concerned with affinity and are more influenced by the popularity of a table
        :param n_iters:
        '''
        self.K = K
        self.alpha = alpha
        self.beta = beta
        self.n_iters = n_iters

    @staticmethod
    def _sample(p):
        '''
        Sample with probability vector p from a multinomial distribution
        :param p: list
            List of probabilities representing probability vector for the multinomial distribution
        :return: int
            index of randomly selected output
        '''
        return [i for i, entry in enumerate(multinomial(1, p)) if entry != 0][0]

    def fit(self, docs, V):
        '''
        Cluster the input documents
        :param docs: list of list
            list of lists containing the unique token set of each document
        :param V: total vocabulary size for each document
        :return: list of length len(doc)
            cluster label for each document
        '''
        alpha, beta, K, n_iters = self.alpha, self.beta, self.K, self.n_iters
        D = len(docs)
        d_z = [None for i in range(D)]
        m_z = [0 for i in range(K)]
        n_z = [0 for i in range(K)]
        n_z_w = [{} for i in range(K)]

        # initialize the clusters
        for i, doc in enumerate(docs):

            # choose a random cluster for the doc
            z = self._sample([1.0 / K for _ in range(K)])
            d_z[i] = z
            m_z[z] += 1
            n_z[z] += len(doc)

            for word in doc:
                if word not in n_z_w[z]:
                    n_z_w[z][word] = 0
                n_z_w[z][word] += 1

        for _iter in range(n_iters):
            total_transfers = 0

            for i, doc in enumerate(docs):

                # remove the doc from it's current cluster
                z_old = d_z[i]

                m_z[z_old] -= 1
                n_z[z_old] -= len(doc)

                for word in doc:
                    n_z_w[z_old][word] -= 1

                    # compact dictionary to save space
                    if n_z_w[z_old][word] == 0:
                        del n_z_w[z_old][word]

                # compute the probability for reassignment
                p = [0 for _ in range(K)]
                for label in range(K):
                    n1 = m_z[label] + alpha
                    lN1 = log(n1) if n1 > 0 else 0
                    lN2 = 0
                    lD1 = log(D - 1 + K * alpha)
                    lD2 = 0
                    for word in doc:
                        lN2 += n_z_w[label].get(word, 0) + beta
                    for j in range(len(doc)):
                        lD2 += n_z[label] + V * beta + j - 1
                    lN2 = log(lN2) if lN2 > 0 else 0
                    lD2 = log(lD2) if lD2 > 0 else 0
                    p[label] = (exp(lN1 - lD1 + lN2 - lD2))

                # draw sample from distribution to find new cluster
                pnorm = sum(p)
                z_new = self._sample([pp / pnorm for pp in p])

                # transfer doc to the new cluster
                if z_new != z_old:
                    total_transfers += 1

                d_z[i] = z_new
                m_z[z_new] += 1
                n_z[z_new] += len(doc)
                for word in doc:
                    if word not in n_z_w[z_new]:
                        n_z_w[z_new][word] = 0
                    n_z_w[z_new][word] += 1
            print("In stage %d: transferred %d clusters with %d clusters populated" % (
            _iter, total_transfers, sum([1 for v in m_z if v > 0])))
        return d_z