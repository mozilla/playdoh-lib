#!/usr/bin/env python

# A very very early start on the road of:
#  git submodule --> installed in lib/python
#
# The reason for temporarily keeping this script around is so it can be used
# for peoples own vendor-local.
#

import re
import os
import subprocess

# the monster command
ARNOLD = ('pip install -I --install-option="--home=`pwd`" --no-deps '
          'git+%s@%s#egg=%s')

def run():
    for each in os.listdir('src'):
        head = os.path.join('src', each, '.git', 'HEAD')
        config = os.path.join('src', each, '.git', 'config')
        if not os.path.isfile(head):
            print "SKIP", each
            continue

        hash = open(head).read().strip()
        url = re.findall('url =\s*(.*)', open(config).read())[0]
        egg = each

        command = ARNOLD % (url, hash, egg)
        print "RUNNING:"
        print command
        proc = subprocess.Popen(command,
            shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        for line in proc.stdout:
            print line
        for line in proc.stderr:
            print "ERROR".ljust(10), line
        print "\n"

if __name__ == '__main__':
    run()
