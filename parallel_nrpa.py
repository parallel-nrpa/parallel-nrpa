#!/usr/bin/env python3

from mpi4py import MPI
from collections import deque
import logging
import time
from deepsense import neptune
import cProfile
import pstats
import sys

import client_server
import nrpa
import rollout
import selector
import reporting


class ParallelNRPAExperiment(client_server.ClientServer):
    def server_loop(self):
#        self._server_loop()
        cProfile.runctx('self._server_loop()', globals(), locals(), 'stats')
        p = pstats.Stats('stats')
        p.sort_stats('cumulative').print_stats(80)

    def report_progress(self, report_sequence=False):
        reporting.log_to_console(self.root)
        if report_sequence:
            reporting.send_sequence(self.neptune_ctx, 'Best sequence', self.root.best_sequence)
        #reporting.send_tree(self.neptune_ctx, 'Rollout tree', self.root.tree())
        self.neptune_ctx.channel_send('Parallel speedup', '{0:.8f}'.format(self.root.parallel_speedup()))
        self.neptune_ctx.channel_send('Progress', '{0:.8f}'.format(self.root.progress()))
        self.neptune_ctx.channel_send('Best sequence length', len(self.root.best_sequence))
        self.neptune_ctx.channel_send('Idle', self.root.idle_time_percent())
        self.neptune_ctx.channel_send('Wall time', self.root.stats['wall_time'])

    def _server_loop(self):
        # Neptune initialization

        self.neptune_ctx = neptune.Context()
        self.neptune_params = self.neptune_ctx.params

        # Rollout tree initialization

        self.root = rollout.RootRollout(iterations=self.neptune_params['iterations'],
                                        parallel_levels=self.neptune_params['parallel_levels'],
                                        atomic_levels=self.neptune_params['atomic_levels'],
                                        alpha=self.neptune_params['alpha'],
                                        random_seed=self.neptune_params['seed'])
        self.root.add_pending_nodes()
        self.node_selector = selector.ProbabilitySelector()

        # Server initialization

        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.nodes = self.comm.Get_size() - 1

        self.workers = deque()
        for worker in range(self.nodes):
            self.workers.append(worker + 1)

        self.working = True
        self.job_source = dict()

        last_logging_time = 0
        last_best_sequence = []

        server_start_time = time.time()

        # seq = 0

        # Server loop
        while self.working:
            # Send jobs
            waiting_rollout = None
            while len(self.workers) > 0:
                waiting_rollout = self.node_selector.select(self.root)
                if waiting_rollout is None:
                    print("NO WAITING ROLLOUTS")
                    break

                job = waiting_rollout.get_computation_metadata()
                waiting_rollout.state = rollout.Rollout.State.running
                waiting_rollout.mark_as_dirty()

                # Send out the job
                worker = self.workers.popleft()
                self.job_source[worker] = job["source"]
                del(job["source"])
                # logging.debug("Sending job {0} to worker {1}".format(job, worker))
                cmd = {'command': 'run', 'payload': job}
                self.comm.send(cmd, dest=worker)

                # Create new waiting nodes
                self.root.update()

            # Finished?
            if waiting_rollout is None and len(self.workers) == self.nodes:
                self.working = False
                break

            # Report progress
            if time.time() - last_logging_time >= 20.0 or \
                    rollout.SequenceComparator.is_right_better(last_best_sequence, self.root.best_sequence):
                last_logging_time = time.time()
                report_sequence = False
                if rollout.SequenceComparator.is_right_better(last_best_sequence, self.root.best_sequence):
                    report_sequence = True
                last_best_sequence = self.root.best_sequence
                self.report_progress(report_sequence)
                #with open("cert.txt", "w") as cert_file:
                #    cert_file.write(str(self.root.atomic_levels) + " ")
                #    cert_file.write(str(self.root.parallel_levels) + " ")
                #    cert_file.write(str(self.root.iterations) + " \n")
                #    self.root.write_cert(cert_file)

            # Retrieve job result
            data = self.comm.recv(source=MPI.ANY_SOURCE)

            logging.debug("Received {1} move sequence from {0}.".format(data["source"], len(data["result"]["best_sequence"])))

#            print("Got result", self.root.tree())

            # Store result and release worker
            self.job_source[data["source"]].record_computation_result(data["result"])
            self.job_source[data["source"]] = None

            # Update statistics
            self.root.stats['idle_time'] += data['stats']['idle_time']
            self.root.stats['wall_time'] = time.time() - server_start_time
            self.root.stats['sequences'] += data['result']['sequences']
            self.root.stats['computation_time'] += data['stats']['computation_time']

            # Release worker
            self.workers.append(data["source"])

            # Update
#            print("before update", self.root.tree())
            self.root.update()
#            print("after update", self.root.tree())

        self.report_progress()
        reporting.log_to_console(self.root)
        print("Best sequence length {0}".format(len(self.root.best_sequence)))

#        self.root.tree(True).render('final.png', w=800, units='px')

        # Terminate workers
        for client in range(self.nodes):
            logging.debug("Sending QUIT command to client {0}.".format(client+1))
            cmd = {'command': 'quit'}
            self.comm.send(cmd, dest=client+1)

    def atomic_computation(self, payload):
        return nrpa.NRPA().run(payload)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    ParallelNRPAExperiment().run()
