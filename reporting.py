from deepsense import neptune
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import morpion
import PIL.Image as Image

def log_to_console(rout):
    logging.info("Time: {0:.2f} wall, {1:.2f} working, {2:.2f} ({3:.0%}) idle".format(
        rout.stats['wall_time'],
        rout.total_time(),
        rout.stats['idle_time'],
        rout.idle_time_percent()
    ))
    logging.info("Sequences: {0}/{1} ({2:.0%}) speedup {3:.2f} done: {4:.0%}".format(
        rout.stats['sequences'], rout.completed_sequences(),
        rout.parallel_efficiency(), rout.parallel_speedup(), rout.progress()))

    logging.info("Root best sequence: {0}".format(len(rout.root.best_sequence)))


def improvement_histogram(self):
    pass


def sequence_diagram(self):
    pass

def send_sequence(ctx, channel_name, sequence):
    game = morpion.Game()
    for move in sequence:
        game.make_move(move)
    grid = game.get_grid()
    grid_image = grid.get_PILImage(800,800)
    neptune_image = neptune.Image(
        name="Morpion Grid",
        description="A sequence of length " + str(len(sequence)),
        data=grid_image)
    ctx.channel_send(channel_name, neptune_image)

def send_histogram(ctx, channel_name, histogram):
    data = copy.copy(histogram)

    while data[-1] == 0:
        data.pop()

    x = [i for i in range(0, len(data))]
    y = data

    fig = plt.figure(figsize=(10, 10), dpi=80)
    ax = fig.add_subplot(111)
    ax.bar(x, y, label='Histogram')
    fig.canvas.draw()
    data = fig.canvas.tostring_rgb()

    histogram_image = Image.frombuffer("RGB", (800, 800), data, "raw", "RGB", 0, 1)

    neptune_image = neptune.Image(name="Histogram",description="Histogram",data=histogram_image)

    ctx.channel_send(channel_name, neptune_image)

def send_tree(ctx, channel_name, tree):
    # tree.render('{0}.png'.format(seq), w=800, units='px')

    #ctx.channel_send(channel_name, str(tree))
    pass