#!/usr/bin/env python3

import mmap
import os
import sys
import unittest
import subprocess

from regression import (
    HAS_SGX,
    RegressionTestCase,
    expectedFailureIf,
)

class TC_00_Unittests(RegressionTestCase):
    def test_000_spinlock(self):
        stdout, stderr = self.run_binary(['spinlock'])

        self.assertIn('Test successful!', stdout)

class TC_01_Bootstrap(RegressionTestCase):
    def test_100_basic_bootstrapping(self):
        stdout, stderr = self.run_binary(['bootstrap'])

        # Basic Bootstrapping
        self.assertIn('User Program Started', stdout)

        # One Argument Given
        self.assertIn('# of Arguments: 1', stdout)
        self.assertIn('argv[0] = bootstrap', stdout)


    def test_101_basic_bootstrapping_five_arguments(self):
        # Five Arguments Given
        stdout, stderr = self.run_binary(['bootstrap', 'a', 'b', 'c', 'd'])
        self.assertIn('# of Arguments: 5', stdout)
        self.assertIn('argv[0] = bootstrap', stdout)
        self.assertIn('argv[1] = a', stdout)
        self.assertIn('argv[2] = b', stdout)
        self.assertIn('argv[3] = c', stdout)
        self.assertIn('argv[4] = d', stdout)

    @unittest.skipUnless(HAS_SGX,
        'This test is only meaningful on SGX PAL because only SGX catches raw '
        'syscalls and redirects to Graphene\'s LibOS. If we will add seccomp to '
        'Linux PAL, then we should allow this test on Linux PAL as well.')
    def test_102_basic_bootstrapping_static(self):
        # bootstrap_static
        stdout, stderr = self.run_binary(['bootstrap_static'])
        self.assertIn('Hello world (bootstrap_static)!', stdout)

    def test_103_basic_bootstrapping_pie(self):
        # bootstrap_pie
        stdout, stderr = self.run_binary(['bootstrap_pie'])
        self.assertIn('User program started', stdout)
        self.assertIn('Local Address in Executable: 0x', stdout)
        self.assertIn('argv[0] = bootstrap_pie', stdout)

    def test_110_basic_bootstrapping_cxx(self):
        stdout, stderr = self.run_binary(['bootstrap-c++'])

        # Basic Bootstrapping (C++)
        self.assertIn('User Program Started', stdout)

    def test_200_exec(self):
        stdout, stderr = self.run_binary(['exec'])

        # 2 page child binary
        self.assertIn(
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 '
            '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 ',
            stdout)

    def test_201_fork_and_exec(self):
        stdout, stderr = self.run_binary(['fork_and_exec'])

        # fork and exec 2 page child binary
        self.assertIn('child exited with status: 0', stdout)
        self.assertIn('test completed successfully', stdout)

    def test_202_vfork_and_exec(self):
        stdout, stderr = self.run_binary(['vfork_and_exec'])

        # vfork and exec 2 page child binary
        self.assertIn('child exited with status: 0', stdout)
        self.assertIn('test completed successfully', stdout)

    def test_210_exec_invalid_args(self):
        stdout, stderr = self.run_binary(['exec_invalid_args'])

        # Execve with invalid pointers in arguments
        self.assertIn(
            'execve(invalid-path) correctly returned error', stdout)
        self.assertIn(
            'execve(invalid-argv-ptr) correctly returned error', stdout)
        self.assertIn(
            'execve(invalid-envp-ptr) correctly returned error', stdout)
        self.assertIn(
            'execve(invalid-argv) correctly returned error', stdout)
        self.assertIn(
            'execve(invalid-envp) correctly returned error', stdout)

    def test_300_shared_object(self):
        stdout, stderr = self.run_binary(['shared_object'])

        # Shared Object
        self.assertIn('Hello world', stdout)

    def test_400_exit(self):
        with self.expect_returncode(113):
            self.run_binary(['exit'])

    @unittest.skipIf(HAS_SGX,
        'Exposes a rare memory corruption on SGX PAL. Disable for now.')
    def test_401_exit_group(self):
        try:
            self.run_binary(['exit_group'])
        except subprocess.CalledProcessError as e:
            self.assertTrue(1 <= e.returncode and e.returncode <= 4)

    def test_402_signalexit(self):
        with self.expect_returncode(134):
            self.run_binary(['abort'])

    def test_403_signalexit_multithread(self):
        with self.expect_returncode(134):
            self.run_binary(['abort_multithread'])

    def test_500_init_fail(self):
        try:
            self.run_binary(['init_fail'])
            self.fail('expected to return nonzero (and != 42)')
        except subprocess.CalledProcessError as e:
            self.assertNotEqual(e.returncode, 42, 'expected returncode != 42')

    def test_600_multi_pthread(self):
        stdout, stderr = self.run_binary(['multi_pthread'])

        # Multiple thread creation
        self.assertIn('128 Threads Created', stdout)

@unittest.skipUnless(HAS_SGX,
    'This test is only meaningful on SGX PAL because only SGX catches raw '
    'syscalls and redirects to Graphene\'s LibOS. If we will add seccomp to '
    'Linux PAL, then we should allow this test on Linux PAL as well.')
class TC_02_OpenMP(RegressionTestCase):
    def test_000_simple_for_loop(self):
        stdout, stderr = self.run_binary(['openmp'])

        # OpenMP simple for loop
        self.assertIn('first: 0, last: 9', stdout)

@unittest.skipUnless(HAS_SGX,
    'This test is only meaningful on SGX PAL because file-check-policy is '
    'only relevant to SGX.')
class TC_03_FileCheckPolicy(RegressionTestCase):
    def test_000_strict_success(self):
        manifest = self.get_manifest('file_check_policy_strict')
        stdout, stderr = self.run_binary([manifest, 'trusted_testfile'])

        self.assertIn('file_check_policy succeeded', stdout)

    def test_001_strict_fail(self):
        manifest = self.get_manifest('file_check_policy_strict')
        try:
            stdout, stderr = self.run_binary([manifest, 'unknown_testfile'])
            self.fail('expected to return nonzero')
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2, 'expected returncode == 2')

    def test_002_allow_all_but_log_success(self):
        manifest = self.get_manifest('file_check_policy_allow_all_but_log')
        stdout, stderr = self.run_binary([manifest, 'unknown_testfile'])

        self.assertIn('Allowing access to an unknown file due to file_check_policy settings: file:unknown_testfile', stderr)
        self.assertIn('file_check_policy succeeded', stdout)

    def test_003_allow_all_but_log_fail(self):
        manifest = self.get_manifest('file_check_policy_allow_all_but_log')
        stdout, stderr = self.run_binary([manifest, 'trusted_testfile'])

        self.assertNotIn('Allowing access to an unknown file due to file_check_policy settings: file:trusted_testfile', stderr)
        self.assertIn('file_check_policy succeeded', stdout)

class TC_30_Syscall(RegressionTestCase):
    def test_000_getcwd(self):
        stdout, stderr = self.run_binary(['getcwd'])

        # Getcwd syscall
        self.assertIn('[bss_cwd_buf] getcwd succeeded: /', stdout)
        self.assertIn('[mmapped_cwd_buf] getcwd succeeded: /', stdout)

    def test_010_stat_invalid_args(self):
        stdout, stderr = self.run_binary(['stat_invalid_args'])

        # Stat with invalid arguments
        self.assertIn('stat(invalid-path-ptr) correctly returned error', stdout)
        self.assertIn('stat(invalid-buf-ptr) correctly returned error', stdout)
        self.assertIn('lstat(invalid-path-ptr) correctly returned error', stdout)
        self.assertIn('lstat(invalid-buf-ptr) correctly returned error', stdout)

    def test_011_fstat_cwd(self):
        stdout, stderr = self.run_binary(['fstat_cwd'])

        # fstat on a directory
        self.assertIn('fstat returned the fd type as S_IFDIR', stdout)

    def test_020_getdents(self):
        # This doesn't catch extraneous entries, but should be fine
        # until the LTP test can be run (need symlink support)

        stdout, stderr = self.run_binary(['getdents'])
        self.assertIn('getdents: setup ok', stdout)

        # Directory listing (32-bit)
        self.assertIn('getdents32: . [0x4]', stdout)
        self.assertIn('getdents32: .. [0x4]', stdout)
        self.assertIn('getdents32: file1 [0x8]', stdout)
        self.assertIn('getdents32: file2 [0x8]', stdout)
        self.assertIn('getdents32: dir3 [0x4]', stdout)

        # Directory listing (64-bit)
        self.assertIn('getdents64: . [0x4]', stdout)
        self.assertIn('getdents64: .. [0x4]', stdout)
        self.assertIn('getdents64: file1 [0x8]', stdout)
        self.assertIn('getdents64: file2 [0x8]', stdout)
        self.assertIn('getdents64: dir3 [0x4]', stdout)

    def test_021_getdents_large_dir(self):
        stdout, stderr = self.run_binary(['large_dir_read', 'tmp/large_dir', '3000'])

        self.assertIn('Success!', stdout)

    def test_030_fopen(self):
        if os.path.exists("tmp/filecreatedbygraphene"):
            os.remove("tmp/filecreatedbygraphene")
        stdout, stderr = self.run_binary(['fopen_cornercases'])

        # fopen corner cases
        self.assertIn('Successfully read from file: Hello World', stdout)

    def test_040_futex_wake(self):
        stdout, stderr = self.run_binary(['futex'])

        # Futex Wake Test
        self.assertIn('Woke all kiddos', stdout)

    def test_041_futex_timeout(self):
        stdout, stderr = self.run_binary(['futex-timeout'])

        # Futex Timeout Test
        self.assertIn('futex correctly timed out', stdout)

    def test_050_mmap(self):
        stdout, stderr = self.run_binary(['mmap-file'], timeout=60)

        # Private mmap beyond file range
        self.assertIn('mmap test 6 passed', stdout)
        self.assertIn('mmap test 7 passed', stdout)

        # Private mmap beyond file range (after fork)
        self.assertIn('mmap test 1 passed', stdout)
        self.assertIn('mmap test 2 passed', stdout)
        self.assertIn('mmap test 3 passed', stdout)
        self.assertIn('mmap test 4 passed', stdout)

    @unittest.skipIf(HAS_SGX,
        'On SGX, SIGBUS isn\'t always implemented correctly, for lack '
        'of memory protection. For now, some of these cases won\'t work.')
    def test_051_mmap_sgx(self):
        stdout, stderr = self.run_binary(['mmap-file'], timeout=60)

        # SIGBUS test
        self.assertIn('mmap test 5 passed', stdout)
        self.assertIn('mmap test 8 passed', stdout)

    def test_52_large_mmap(self):
        stdout, stderr = self.run_binary(['large-mmap'], timeout=480)

        # Ftruncate
        self.assertIn('large-mmap: ftruncate OK', stdout)

        # Large mmap
        self.assertIn('large-mmap: mmap 1 completed OK', stdout)
        self.assertIn('large-mmap: mmap 2 completed OK', stdout)

    @unittest.skip('sigaltstack isn\'t correctly implemented')
    def test_060_sigaltstack(self):
        stdout, stderr = self.run_binary(['sigaltstack'])

        # Sigaltstack Test
        self.assertIn('OK on sigaltstack in main thread before alarm', stdout)
        self.assertIn('&act == 0x', stdout)
        self.assertIn('sig 14 count 1 goes off with sp=0x', stdout)
        self.assertIn('OK on signal stack', stdout)
        self.assertIn('OK on sigaltstack in handler', stdout)
        self.assertIn('sig 14 count 2 goes off with sp=0x', stdout)
        self.assertIn('OK on signal stack', stdout)
        self.assertIn('OK on sigaltstack in handler', stdout)
        self.assertIn('sig 14 count 3 goes off with sp=0x', stdout)
        self.assertIn('OK on signal stack', stdout)
        self.assertIn('OK on sigaltstack in handler', stdout)
        self.assertIn('OK on sigaltstack in main thread', stdout)
        self.assertIn('done exiting', stdout)

    def test_070_eventfd(self):
        stdout, stderr = self.run_binary(['eventfd'])

        # Eventfd Test
        self.assertIn('eventfd_using_poll completed successfully', stdout)
        self.assertIn('eventfd_using_various_flags completed successfully', stdout)

    def test_080_sched(self):
        stdout, stderr = self.run_binary(['sched'])

        # Scheduling Syscalls Test
        self.assertIn('Test completed successfully', stdout)

@unittest.skipUnless(HAS_SGX,
    'This test is only meaningful on SGX PAL because only SGX catches raw '
    'syscalls and redirects to Graphene\'s LibOS. If we will add seccomp to '
    'Linux PAL, then we should allow this test on Linux PAL as well.')
class TC_31_SyscallSGX(RegressionTestCase):
    def test_000_syscall_redirect(self):
        stdout, stderr = self.run_binary(['syscall'])

        # Syscall Instruction Redirection
        self.assertIn('Hello world', stdout)

class TC_40_FileSystem(RegressionTestCase):
    def test_000_base(self):
        stdout, stderr = self.run_binary(['proc'])

        # Base /proc files present
        self.assertIn('/proc/1/..', stdout)
        self.assertIn('/proc/1/cwd', stdout)
        self.assertIn('/proc/1/exe', stdout)
        self.assertIn('/proc/1/root', stdout)
        self.assertIn('/proc/1/fd', stdout)
        self.assertIn('/proc/1/maps', stdout)
        self.assertIn('/proc/.', stdout)
        self.assertIn('/proc/1', stdout)
        self.assertIn('/proc/self', stdout)
        self.assertIn('/proc/meminfo', stdout)
        self.assertIn('/proc/cpuinfo', stdout)

    def test_010_path(self):
        stdout, stderr = self.run_binary(['proc-path'])

        # Base /proc path present
        self.assertIn('proc path test success', stdout)

    def test_020_cpuinfo(self):
        stdout, stderr = self.run_binary(['proc_cpuinfo'], timeout=50)

        # proc/cpuinfo Linux-based formatting
        self.assertIn('cpuinfo test passed', stdout)

    def test_030_fdleak(self):
        stdout, stderr = self.run_binary(['fdleak'], timeout=10)
        self.assertIn("Test succeeded.", stdout)

class TC_80_Socket(RegressionTestCase):
    def test_000_getsockopt(self):
        stdout, stderr = self.run_binary(['getsockopt'])
        self.assertIn('getsockopt: Got socket type OK', stdout)

    def test_010_epoll_wait_timeout(self):
        stdout, stderr = self.run_binary(['epoll_wait_timeout', '8000'],
            timeout=50)

        # epoll_wait timeout
        self.assertIn('epoll_wait test passed', stdout)

    def test_100_socket_unix(self):
        stdout, stderr = self.run_binary(['unix'])
        self.assertIn('Data: This is packet 0', stdout)
        self.assertIn('Data: This is packet 1', stdout)
        self.assertIn('Data: This is packet 2', stdout)
        self.assertIn('Data: This is packet 3', stdout)
        self.assertIn('Data: This is packet 4', stdout)
        self.assertIn('Data: This is packet 5', stdout)
        self.assertIn('Data: This is packet 6', stdout)
        self.assertIn('Data: This is packet 7', stdout)
        self.assertIn('Data: This is packet 8', stdout)
        self.assertIn('Data: This is packet 9', stdout)

    def test_200_socket_udp(self):
        stdout, stderr = self.run_binary(['udp'], timeout=50)
        self.assertIn('Data: This is packet 0', stdout)
        self.assertIn('Data: This is packet 1', stdout)
        self.assertIn('Data: This is packet 2', stdout)
        self.assertIn('Data: This is packet 3', stdout)
        self.assertIn('Data: This is packet 4', stdout)
        self.assertIn('Data: This is packet 5', stdout)
        self.assertIn('Data: This is packet 6', stdout)
        self.assertIn('Data: This is packet 7', stdout)
        self.assertIn('Data: This is packet 8', stdout)
        self.assertIn('Data: This is packet 9', stdout)
