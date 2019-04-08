"""
Client/Server code that distributes calculations across multiple nodes.
"""

import logging
import time
from collections import deque
from mpi4py import MPI
from deepsense import neptune

import gc

class ClientServer:
    def server_loop(self):
        """Server loop."""
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.nodes = self.comm.Get_size() - 1
        self.ctx = neptune.Context()
        self.params = self.ctx.params
        self.job_queue = deque()
        self.working = True
        self.is_paused = False

        logging.info("Started server for {0} nodes.".format(self.nodes))

        self.available_workers = deque([i + 1 for i in range(self.nodes)])

        self.initialize_job_queue()

        while self.working:
            # Dispatch queued jobs to available workers
            while self.available_workers and self.job_queue and not self.is_paused:
                job = self.job_queue.popleft()
                worker = self.available_workers.popleft()
                logging.debug("Sending job to worker {0}".format(worker))

                cmd = {'command':'run', 'payload': job}
                self.comm.send(cmd, dest=worker)

            # Collect and process computation result
            data = self.comm.recv(source=MPI.ANY_SOURCE)
            logging.debug("Received computation result from client {0}.".format(data['source']))

            self.available_workers.append(data['source'])
            self.job_completed(data['result'])

        if len(self.available_workers) < self.nodes:
            logging.error("quit() called with pending computations.")

        # Send quit commands
        for client in range(self.nodes):
            logging.debug("Sending QUIT command to client {0}.".format(client+1))
            cmd = {'command': 'quit'}
            self.comm.send(cmd, dest=client+1)

    def client_loop(self):
        """Client loop."""
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.nodes = self.comm.Get_size() - 1

        logging.info("Starting client {0}/{1}.".format(self.rank, self.nodes))

        self.stats = dict()

        self.stats["computation_time"] = 0
        self.stats["idle_time"] = 0

        time_checkpoint = time.time()

        while True:
            # logging.debug("Client {0} is waiting for a job.".format(self.rank))

            data = self.comm.recv(source=0)

            if data['command'] == 'quit':
                logging.info("Stopping client {0}.".format(self.rank))
                break
            elif data['command'] == 'run':

                time_measurement = time.time()
                self.stats["idle_time"] = time_measurement - time_checkpoint
                time_checkpoint = time_measurement

                logging.debug("Process {0} received RUN command.".format(self.rank))
                result = self.atomic_computation(data['payload'])
                gc.collect()
                logging.debug("Process {0} finished computation.".format(self.rank))

                time_measurement = time.time()
                self.stats["computation_time"] = time_measurement - time_checkpoint
                time_checkpoint = time_measurement

                result['computation_time'] = self.stats["computation_time"]

                self.comm.send({"source": self.rank, "result": result, "stats": self.stats}, dest=0)

    def run(self):
        """Entry point."""
        if MPI.COMM_WORLD.Get_rank() == 0:
            self.server_loop()
            logging.info("Server terminated.")
        else:
            self.client_loop()
            logging.info("Client {0} terminated.".format(self.rank))

    def queue_job(self, payload):
        logging.debug("Queuing job with payload {0} ({1} jobs "
                      "in queue)".format(payload, len(self.job_queue)))
        self.job_queue.append(payload)

    def quit(self):
        """Stop workers, reporting.py final results and quit.

        Can be called only at the server node.
        """

        if self.rank != 0:
            logging.error("quit() called at a client node.")
            return

        self.working = False

    def pause(self, argument):
        """Stop sending jobs to clients."""
        logging.info("pause called with argument {0}".format(argument))
        self.is_paused = True

    def resume(self):
        """Resume sending jobs to clients."""
        self.is_paused = False

        # TODO - when actions will work: wake up the server loop

    def save_checkpoint(self):
        """Save computation state.

        Can be called only at the server node when there are no active computations
        on client nodes.
        """
        pass

    def load_checkpoint(self):
        """Load computation state.

        Can be called only at the server node when there are no active computations
        on client nodes.
        """
        pass

    def check_parameters(self, parameter_list):
        for parameter in parameter_list:
            if parameter not in self.params:
                logging.error('Missing experiment parameter "{0}"'.format(parameter))

    # Experiment specific methods - server-side
    def job_completed(self, result):
        pass

    def initialize_job_queue(self):
        self.quit()

    def report_final_result(self):
        pass

    # Experiment specific methods - client-side
    def atomic_computation(self, payload):
        pass
