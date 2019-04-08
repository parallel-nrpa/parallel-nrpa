"""
NRPA Rollout data structures.
"""

import enum
import numpy as np
import ete3
import copy
import policy
from collections import deque


class SequenceComparator:
    """Comparator for Morpion sequences."""

    iter = 1
    set = np.zeros((10000,), dtype=int)

    @staticmethod
    def is_equal(left, right):
        """Fuzzy equality test."""

        if len(left) != len(right):
            return False
        SequenceComparator.iter += 1

        for i in left:
            SequenceComparator.set[i] = SequenceComparator.iter

        diffs = 0
        for i in right:
            if SequenceComparator.set[i] != SequenceComparator.iter:
                diffs += 1
                if diffs > len(left) * 0.3:
                    return False

        return True

    @staticmethod
    def is_right_better(left, right):
        """Fuzzy strict inequality test."""
        return len(left) < len(right) or (len(left) == len(right)
                                          and not SequenceComparator.is_equal(left, right))


class Rollout:
    """Abstract base class for RootRollout, ParallelRollout and AtomicRollout."""

    class State(enum.Enum):
        """State of a rollout."""

        pending = 0     #: There are no calculations running. There are pending calculations.
        running = 1     #: There is at least one running calculation.
        completed = 2   #: The rollout is complete.

    def __init__(self):
        self.state = Rollout.State.pending
        self.sibling = None
        self.parent = None
        self.adapt_sequence = None
        self.best_sequence = []
        self.policy = None
        self.dirty = False
        self.root = None
        self.depth = None
        self.completed_nodes = None
        self.active_pool = deque()

    def mark_as_dirty(self):
        node = self
        while node is not None:
            node.dirty = True
            node = node.parent

    def adapt(self):
        """Adapt policy of sibling with parent's predicted best sequence."""

        if self.parent is None:
            # We are the root node
            self.policy = policy.WeightPolicy()
            self.adapt_sequence = []
        else:
            if self.sibling is None:
                # First node in a rollout copies parent policy
                self.adapt_sequence = []
                self.policy = copy.copy(self.parent.policy)
            else:
                self.adapt_sequence = copy.copy(self.parent.predicted_best_sequence())
                self.policy = copy.copy(self.sibling.policy)
                self.policy.adapt(self.adapt_sequence)

    def update(self) -> None:
        """Update rollout tree and clear dirty bits."""
        raise NotImplementedError

    def tree(self) -> ete3.Tree:
        """Returns ete3.Tree representing the rollout."""
        raise NotImplementedError

    def discard(self):
        """For each leaf node: remove if it is pending or completed; put into root's
        discarded_pool if it is running."""

        raise NotImplementedError

    def is_atomic(self):
        return False


class ParallelRollout(Rollout):
    def discard(self):
        """Inner nodes are forgotten on discard. Propagate to leaf nodes."""

        for rout in self.active_pool:
            rout.discard()

        del self.parent

    def predicted_best_sequence(self):
        """Predicted best sequence if rollouts completed in future will be validated."""
        sequence = self.best_sequence
        for node in self.active_pool:
            node_sequence = node.predicted_best_sequence()
            if SequenceComparator.is_right_better(sequence, node_sequence):
                sequence = node_sequence

        return copy.copy(sequence)

    def tree(self) -> ete3.Tree:
        """Create ete3.Tree representing rollout structure."""
        if self.state == Rollout.State.pending:
            tree = ete3.Tree('P {0} {1} |{2}|;'.format(self.node_id, len(self.best_sequence),
                                                       len(self.adapt_sequence)))
        elif self.state == Rollout.State.running:
            tree = ete3.Tree('R {0} {1} |{2}|;'.format(self.node_id, len(self.best_sequence),
                                                       len(self.adapt_sequence)))
        else:
            tree = ete3.Tree('C {0} {1} |{2}|;'.format(self.node_id, len(self.best_sequence),
                                                       len(self.adapt_sequence)))

        for r in self.active_pool:
            tree.add_child(r.tree())

        return tree

    def __init__(self, parent, node_id):
        """Sets sibling and adapts policy."""

        super().__init__()

        self.state = Rollout.State.pending
        self.parent = parent
        self.node_id = node_id
        self.best_sequence = []
        self.completed_nodes = 0

        depth = 0
        root = self
        while root.parent is not None:
            depth += 1
            root = root.parent
        self.root = root
        self.depth = depth

        self.sibling = self.parent.youngest_child() if self.parent is not None else None
        self.adapt()

    def youngest_child(self):
        """Return last rollout from active_pool."""

        return self.active_pool[-1] if len(self.active_pool) > 0 else None

    def add_pending_nodes(self):
        """Add a pending child if we don't have one and if we have capacity."""

        if len(self.active_pool) + self.completed_nodes >= self.root.iterations:
            return False

        node_id = self.node_id * self.root.iterations + len(self.active_pool) + self.completed_nodes

        if self.root.parallel_levels - self.depth <= 1:
            rollout = AtomicRollout(parent=self, node_id=node_id)
        else:
            rollout = ParallelRollout(parent=self, node_id=node_id)
            rollout.add_pending_nodes()

        self.active_pool.append(rollout)
        return True

    def update(self):
        """Update rollout structure after computation result was posted."""

        if not self.dirty:
            return

        # Find the dirty node and the next node
        dirty_node = None
        next_node = None
        children_iterator = iter(self.active_pool)
        for node in children_iterator:
            if node.dirty:
                dirty_node = node
                next_node = next(children_iterator, None)
                break

        if dirty_node is None:
            # dirty_node was discarded
            self.dirty = False
            return

        # Update the dirty node
        dirty_node.update()

        # Discard nodes after the dirty node if the sequence is not consistent
        if next_node is not None:
            if SequenceComparator.is_right_better(next_node.adapt_sequence,
                                                  dirty_node.predicted_best_sequence()):
                while not self.active_pool[-1].dirty:
                    self.active_pool.pop().discard()

        # Update our best sequence, starting with next_node sequence
        found_dirty = False
        for node in self.active_pool:
            if node.dirty:
                found_dirty = True
            if found_dirty:
                if SequenceComparator.is_right_better(self.best_sequence, node.best_sequence):
                    self.best_sequence = copy.copy(node.best_sequence)
            if node.state != Rollout.State.completed:
                break

        # What types of children do we have
        has_running = False
        has_pending = False

        for node in self.active_pool:
            if node.state == Rollout.State.running:
                has_running = True
            if node.state == Rollout.State.pending:
                has_pending = True

        # Add pending child if we don't have one
        if not has_pending:
            has_pending = self.add_pending_nodes()

        # Update state
        if has_running:
            self.state = Rollout.State.running
        elif has_pending:
            self.state = Rollout.State.pending
        else:
            self.state = Rollout.State.completed

            assert len(self.active_pool) + self.completed_nodes == self.root.iterations

        # Delete completed nodes
        while len(self.active_pool) > 1 and self.active_pool[0].state == Rollout.State.completed:
            self.active_pool.popleft()
            self.completed_nodes += 1

        if len(self.active_pool) > 0:
            self.active_pool[0].sibling = None

        # Clear the dirty bit
        dirty_node.dirty = False


class RootRollout(ParallelRollout):
    """RootRollout stores metadata and computation statistics."""

    def discard(self):
        # root rollout should never be discarded
        assert False

    def __init__(self, random_seed=1, parallel_levels=2, atomic_levels=2,
                 iterations=100, alpha=1.0):

        super().__init__(None, 0)

        self.discarded_pool = []

        self.node_id = 0
        self.state = Rollout.State.pending
        self.root = self

        self.random_seed = random_seed
        self.iterations = iterations
        self.parallel_levels = parallel_levels
        self.atomic_levels = atomic_levels
        self.alpha = alpha

        # Statistics initialization
        self.stats = dict()
        self.stats["root_random_seed"] = self.random_seed
        self.stats["wall_time"] = 0
        self.stats["idle_time"] = 0
        self.stats["sequences"] = 0
        self.stats['computation_time'] = 0

        self.stats['completed_atomic'] = 0
        self.stats['discarded_atomic'] = 0

        # Initialization of random seeds for atomic rollouts
        np.random.seed(self.random_seed)
        self.seeds = np.random.randint(1, 1000000000, self.iterations ** self.parallel_levels)

    def update(self):
        super().update()

        # Dirty state is cleared by parent, unless we are the root node
        self.dirty = False

    def atomic_random_seed(self, n):
        """Retrieve deterministic random seed for an atomic node."""
        assert n < self.seeds.shape[0]

        return self.seeds[n]

    # Statistics

    def total_time(self):
        return self.stats['computation_time'] + self.stats['idle_time']

    def idle_time_percent(self):
        if self.total_time() == 0:
            return 0.0

        return self.stats['idle_time'] / self.total_time()

    def parallel_speedup(self):
        """Efficiency * Total computation time / Wall time"""
        if self.stats['wall_time'] == 0:
            return 1.0

        return self.parallel_efficiency() * self.stats['computation_time'] / self.stats['wall_time']

    # Reporting

    def parallel_efficiency(self):
        # Used computations to total computations (%)
        if self.stats['sequences'] == 0:
            return 1.0

        return self.completed_sequences() / self.stats['sequences']

    def completed_sequences(self):
        return (self.stats['completed_atomic'] - self.stats['discarded_atomic']) * \
               (self.iterations ** self.atomic_levels)

    def total_expected_sequences(self):
        return self.iterations ** (self.parallel_levels + self.atomic_levels)

    def progress(self):
        if self.stats['sequences'] == 0:
            return 0.0

        return self.completed_sequences() / self.total_expected_sequences()


class AtomicRollout(Rollout):
    def __init__(self, parent=None, node_id=None):
        """Adapts policy of youngest sibling."""

        super().__init__()

        self.state = Rollout.State.pending
        self.parent = parent
        root = self
        while root.parent is not None:
            root = root.parent
        self.root = root
        self.node_id = node_id
        self.sibling = self.parent.youngest_child()
        self.adapt()
        self.atomic_random_seed = None

        # Stats
        self.computation_time = 0.0

    def discard(self):
        self.parent = None

        assert self not in self.root.discarded_pool

        if self.state == Rollout.State.running:
            self.root.discarded_pool.append(self)
        if self.state == Rollout.State.completed:
            self.root.stats['discarded_atomic'] += 1
        else:
            pass

    def update(self):
        pass

    def tree(self):
        label = '{0} {1}/{2}'.format(self.node_id, len(self.best_sequence),
                                     len(self.adapt_sequence))

        if self.state == Rollout.State.pending:
            label = 'P {0}'.format(label)
        elif self.state == Rollout.State.running:
            label = 'R {0}'.format(label)
        else:
            label = 'C {0}'.format(label)

        node = ete3.Tree()
        node.name = label

        return node

    def is_atomic(self):
        return True

    # Methods specific to AtomicRollout
    def get_computation_metadata(self):
        assert self.state == Rollout.State.pending

        return {'source': self,
                'iterations': self.root.iterations,
                'levels': self.root.atomic_levels,
                'batch_size': 1,
                'alpha': self.root.alpha,
                'random_seed': self.root.atomic_random_seed(self.node_id),
                'weights': self.policy}

    def record_computation_result(self, result):
        assert self.state == Rollout.State.running

        self.state = Rollout.State.completed
        self.mark_as_dirty()
        self.best_sequence = copy.copy(result['best_sequence'])
        self.atomic_random_seed = result['random_seed']

        self.root.stats['completed_atomic'] += 1

        if self in self.root.discarded_pool:
            self.root.stats['discarded_atomic'] += 1
            self.root.discarded_pool.remove(self)

    def predicted_best_sequence(self):
        return self.best_sequence
