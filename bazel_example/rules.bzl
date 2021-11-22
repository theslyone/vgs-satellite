TAG = '49'

def _dbg_example_impl(ctx):
    for i in range(5):
        print('interation: {}'.format(i))


dbg_example = rule(
    implementation = _dbg_example_impl,
)
