#!/usr/bin/python2.4

"""Helper script for extending subversion functionality."""

import commands
import os
import sys

class SVNHelper(object):
  """Class implementing svn helper methods."""

  # Commands that this class knows how to do and the methods to call to do them.
  COMMANDS = {'diffstats': 'DiffStats'}

  def Process(self, argv):
    """Process a command line."""
    if argv[0] in self.COMMANDS:
      return self.__getattribute__(self.COMMANDS[argv[0]])(argv[1:])
    argv.insert(0, 'svn')
    os.execvp('svn', argv)

  def DiffStats(self, argv):
    """Generate some stats about the current diff target."""
    cmd = 'svn diff ' + ' '.join(argv)
    (status, output) = commands.getstatusoutput(cmd)
    status = status>>8
    if status:
      print "command: '%s'" % cmd
      return (status, output)

    self.stats = {'plus': 0, 'minus': 0}
    self.all_stats = {'added': 0, 'removed': 0, 'changed': 0, 'files': 0}
    self.inside_block = False
    def ProcessBlock():
      """Assimilate any stats from the current block."""
      if self.inside_block:
        if self.stats['plus'] > self.stats['minus']:
          self.all_stats['changed'] += self.stats['minus']
          self.all_stats['added'] += self.stats['plus'] - self.stats['minus']
        else:
          self.all_stats['changed'] += self.stats['plus']
          self.all_stats['removed'] += self.stats['minus'] - self.stats['plus']
        self.inside_block = False
        self.stats['plus'] = 0
        self.stats['minus'] = 0

    for line in output.split('\n'):
      # "---" and "+++" are file markers, only count one of them.
      if line.startswith('---'):
        self.all_stats['files'] += 1
        ProcessBlock()
      elif line.startswith('+++'):
        ProcessBlock()
      elif line.startswith('-'):
        self.stats['minus'] += 1
        self.inside_block = True
      elif line.startswith('+'):
        self.stats['plus'] += 1
        self.inside_block = True
      elif self.inside_block:
        ProcessBlock()

    output = "files: %d; lines: changed %d, added %d, removed %d" % (
        self.all_stats['files'], self.all_stats['changed'],
        self.all_stats['added'], self.all_stats['removed'])
    return (0, output)


def main(argv):
  helper = SVNHelper()
  (status, output) = helper.Process(argv[1:])
  print output
  sys.exit(status)

if __name__ == '__main__':
  main(sys.argv)
