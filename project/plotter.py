from __future__ import absolute_import as _absolute_import
import operator
import numpy as np

def plot(solution, shifts_spec, slot_min, num_days, shift_colors, resources, img_filename=None,resource_height=1.0,show_task_labels=True,
         color_prec_groups=False,hide_tasks=[],hide_resources=[],task_colors=dict(),fig_size=(15,5),
     vertical_text=False) :
    """
    Plot the given solved solution using matplotlib

    Args:
    solution:    solution to plot
    msg:         0 means no feedback (default) during computation, 1 means feedback
    """
    try :
        import matplotlib
        if img_filename is not None:
            matplotlib.use('Agg')
        import matplotlib.patches as patches, matplotlib.pyplot as plt
    except :
        raise Exception('ERROR: matplotlib is not installed')
    import random

    fig, ax = plt.subplots(1, 1, figsize=fig_size)
    plt.ylim(0, solution['total_resources'])

    ts = int(60.0 / slot_min)
    plt.xlim(0, num_days * 24)

    for i in solution['resource_shifts']:
        r = i['resource']
        id = resources.index(r)
        day = i['day']
        shift_hours = shifts_spec[i['shift']]

        for idx, j in enumerate(shift_hours):
            if(j > 0):
                ax.add_patch(
                    patches.Rectangle(
                    (day * 24 + idx / ts, id),       # (x,y)
                    1 / ts,   # width (1h)
                    resource_height,   # height
                    color = shift_colors[i['shift']],
                    alpha=0.6
                    )
        )

    all_res = list(map(lambda x: {'id': resources.index(x['resource']), 'resource': x['resource']}, solution['resource_shifts']))
    uniq_res = list({resources.index(v['resource']):v for v in all_res}.values())
    plt.yticks([x + resource_height/2.0 for x in range(len(uniq_res))], [i['resource'] for i in uniq_res])
    plt.xticks(np.arange(0, num_days * 24 + 1, 12))
    plt.title(f'Employee Scheduling: {len(uniq_res)} employees, {num_days} days ({num_days * 24} hours)')

    if img_filename is not None:
        fig.figsize=(1,1)
        plt.savefig(img_filename,dpi=200,bbox_inches='tight')
    else :
        plt.show()
