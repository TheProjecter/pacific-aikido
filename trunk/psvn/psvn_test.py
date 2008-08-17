#!/usr/bin/python2.4

import psvn

import textwrap
import unittest

class SVNHelperTest(unittest.TestCase):
  """Tests for SVNHelper class."""

  def setUp(self):
    self._helper = psvn.SVNHelper()
    self._mocks = {}

  def tearDown(self):
    self.UnMockAll()

  def Mock(self, module, mock_target, mock_object):
    self._mocks.setdefault(module, []).append((mock_target,
                                               getattr(module, mock_target)))
    setattr(module, mock_target, mock_object)

  def UnMockAll(self):
    for target_module in self._mocks:
      for mocked_object_name, orig_object in self._mocks[target_module]:
        setattr(target_module, mocked_object_name, orig_object)

  def MockOutExecvp(self):
    """Mock out psvn.execvp in a predictable way.

    Provides boolean self.mock_execvp_was_called for testing whether the mock
    execvp method was called.
    """
    self.mock_execvp_was_called = False

    def MockExecvp(cmd, args):
      self.assertEqual(cmd, 'svn')
      self.mock_execvp_was_called = True

    self.Mock(psvn.os, 'execvp', MockExecvp)

  def testProcessDelegatesUnknownOps(self):
    """Process should delegate unknown operatons to the real svn."""
    self.MockOutExecvp()
    self._helper.Process(['nosuchcommand', 'arg1', 'arg2'])
    self.assertTrue(self.mock_execvp_was_called)

  def testProcess(self):
    """Process should invoke known operations."""
    self.mock_cmd_was_called = False

    def MockCmd(args):
      self.mock_cmd_was_called = True

    self.Mock(self._helper, 'COMMANDS', {'fake_cmd': ('FakeCmd', 'help')})
    setattr(self._helper, 'FakeCmd', MockCmd)

    self._helper.Process(['fake_cmd'])
    self.assertTrue(self.mock_cmd_was_called)

  def testDiffStats(self):
    """DiffStats should return correct results."""
    self.mock_diff_was_called = False
    self.status = 0

    def MockDiff(cmd):
      self.mock_diff_was_called = True
      self.assertTrue(cmd.startswith('svn diff'))
      diff_output = textwrap.dedent("""
          Index: SomeFile
          ===================================================================
          --- SomeFile     (revision 528)
          +++ SomeFile     (working copy)
          @@ -135,28 +135,32 @@


          - remove a line

          + add a line

          - change this line
          + into another one

          blah blah blah
          """)
      return (self.status, diff_output)

    self.Mock(psvn.commands, 'getstatusoutput', MockDiff)
    (status, output) = self._helper.Process(['diffstats'])
    self.assertEqual(output, 'files: 1; lines: changed 1, added 1, removed 1')
    self.assertEqual(status, self.status)
    self.assertTrue(self.mock_diff_was_called)

  def testHelp(self):
    """Help messages should work."""
    self.MockOutExecvp()

    def TestHelp(help_args):
      """Fetch help messages."""
      help_args.insert(0, 'help')
      status, output = self._helper.Process(help_args)
      self.assertEqual(0, status)
      self.assertTrue(output)

    # Overall help.
    TestHelp([])
    # Help for subcommands.
    for subcmd in self._helper.COMMANDS:
      TestHelp([subcmd])
    # Verify that nothing was passed through to svn.
    self.assertFalse(self.mock_execvp_was_called)


if __name__ == '__main__':
  unittest.main()
