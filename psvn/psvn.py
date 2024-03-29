#!/usr/bin/python2.4

"""Helper script for extending subversion functionality."""

import commands
import getopt
import os
import sys
import textwrap


class Error(Exception):
  """Top-level exception class."""


class UnrecognizedOption(Error):
  """A subcommand saw an option it did not know how to handle."""


class SVNHelper(object):
  """Class implementing svn helper methods."""

  # Commands that this class knows how to process.  Format:
  # 'command_name': (CmdMethod, UsageMsg)
  # where CmdMethod is the name of the method to call to execute the command
  # and UsageMsg is a string containing the subcommand's usage message.
  COMMANDS = {
      'diffstats': (
          'DiffStats',
          textwrap.dedent("""
              %(command)s: Generate statistics about a diff.
              usage: %(command)s [FLAGS]

              Options:
                As per 'svn diff'.
              """)),
      'help': (
          'Help',
          textwrap.dedent("""
              %(command)s: Print usage messages.
              usage: %(command)s [SUBCOMMAND...]
              """)),
      'rollback': (
          'Rollback',
          textwrap.dedent("""
              %(command)s: Roll back a change.
              usage: %(command)s (-c <change>|-r <rev>)

              Options:
                -c <change>  Roll back a single change.
                -r <rev>     Roll back from HEAD to a given revision.
              """)),
  }

  def DeletegateToSVN(self, argv):
    """Pass command through to svn."""
    argv.insert(0, 'svn')
    os.execvp('svn', argv)

  def Process(self, argv):
    """Process a command line."""
    if argv[0] in self.COMMANDS:
      return self.__getattribute__(self.COMMANDS[argv[0]][0])(argv[1:])
    self.DeletegateToSVN(argv)

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

    files = self.all_stats['files']
    changed = self.all_stats['changed']
    added = self.all_stats['added']
    removed = self.all_stats['removed']
    output = "files: %d; %d delta lines: changed %d, added %d, removed %d" % (
        files, (changed + added + removed), changed, added, removed)
    return (0, output)

  def Help(self, argv):
    """Print usage messages."""
    output = ''
    if not argv:
      output = textwrap.dedent("""
          usage: %s <subcommand> [options] [args]
          (Type 'svn help" for help on svn native commands.)

          Available subcommands:
          """ % (sys.argv[0],))
      output += ''.join(['   %s\n' % c for c in sorted(self.COMMANDS.keys())])
    elif argv[0] in self.COMMANDS:
      output = self.COMMANDS[argv[0]][1] % {'command': argv[0]}
    else:
      argv.insert(0, 'help')
      self.DeletegateToSVN(argv)
    return (0, output.lstrip('\n'))

  def Rollback(self, argv):
    """Roll back a change."""
    revisions = None

    try:
      opts, args = getopt.getopt(argv, 'c:r:')
    except getopt.GetoptError, e:
      return (1, 'Bad argument: %s' % e)

    if args:
      return (1, 'Extra arguments to rollback: %s' % ' '.join(args))

    for opt, arg in opts:
      if opt == '-c' or opt == '-r':
        try:
          rollback_rev = int(arg)
        except ValueError:
          return (1, 'Must specify a numeric argument for %s' % opt)
        if rollback_rev < 0:
          return (1, 'Must specify a positive numeric argument for %s' % opt)
        if opt == '-c':
          revisions =  (rollback_rev, rollback_rev - 1)
        else:
          revisions =  ('HEAD', rollback_rev - 1)

      else:
        # This should never happen; it is a mismatch between the option list
        # passed to getopt and the option list handled in this for loop.
        raise UnrecognizedOption(opt)

    if revisions is None:
      return (1, 'Must specify -c or -r')

    self.DeletegateToSVN(['merge', '-r', '%s:%i' % revisions, '.'])


def main(argv):
  helper = SVNHelper()
  (status, output) = helper.Process(argv[1:])
  print output
  sys.exit(status)

if __name__ == '__main__':
  main(sys.argv)
