#!/usr/bin/perl

use strict;
use warnings;

use lib 't/lib';

use English qw(-no_match_vars);
use Test::More;
use Test::MockModule;
use Test::NoWarnings;


BEGIN {
    # use mock modules for non-available ones
    push @INC, 't/lib/fake/windows' if $OSNAME ne 'MSWin32';
}

use GLPI::Agent::Tools::Win32;
use GLPI::Agent::Task::Inventory::Generic::Remote_Mgmt::MeshCentral;

# Registry content of HKLM/SOFTWARE/Open Source/ as returned by getRegistryKey(required => NodeId)
my %cases = (
    'default agent' => {
        key    => { 'Mesh Agent/' => { '/NodeId' => 'DEFAULTNODEID' } },
        nodeid => 'DEFAULTNODEID',
    },
    'branded agent (agentCustomization serviceName)' => {
        key    => {
            'AbundantLogicRemote/' => { '/NodeId' => 'PIbHM0sidc8LrESkEI1o0Jx25rIN4uyBzRPtfg8y6kqL3$r$uX5dBsdrUi041yZK' },
            'MeshAgent2/'          => { },
        },
        nodeid => 'PIbHM0sidc8LrESkEI1o0Jx25rIN4uyBzRPtfg8y6kqL3$r$uX5dBsdrUi041yZK',
    },
    'default agent preferred over branded' => {
        key    => {
            'AbundantLogicRemote/' => { '/NodeId' => 'BRANDED' },
            'Mesh Agent/'          => { '/NodeId' => 'DEFAULT' },
        },
        nodeid => 'DEFAULT',
    },
    'no agent' => {
        key    => { 'MeshAgent2/' => { } },
        nodeid => undef,
    },
);

plan tests => scalar(keys %cases) + 1;


# On non-Windows the fake Win32API::Registry makes getRegistryKeyValue() try real registry calls on our
# plain hashes, so read the test data directly (what it does in remote-inventory mode).
my $win32 = Test::MockModule->new('GLPI::Agent::Tools::Win32');
$win32->mock(getRegistryKeyValue => sub { my ($key, $name) = @_; return $key->{"/$name"}; });

foreach my $case (sort keys %cases) {
    # mock in GLPI::Agent::Tools::Win32 itself: _winBased() re-imports it with ->use() on each call
    $win32->mock(getRegistryKey => sub { return $cases{$case}->{key}; });
    my $nodeid = GLPI::Agent::Task::Inventory::Generic::Remote_Mgmt::MeshCentral::_winBased();
    is($nodeid, $cases{$case}->{nodeid}, "MeshCentral NodeId: $case");
}
