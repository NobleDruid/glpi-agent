package GLPI::Agent::Task::Inventory::Generic::Remote_Mgmt::MeshCentral;

use strict;
use warnings;

use parent 'GLPI::Agent::Task::Inventory::Module';

use English qw(-no_match_vars);

use GLPI::Agent::Tools;

my @linuxPath = qw(
    /etc/systemd/system/meshagent.service
    /usr/lib/systemd/system/meshagent.service
    /lib/systemd/system/meshagent.service
);

sub isEnabled {
    my (%params) = @_;

    if (OSNAME eq 'MSWin32') {

        GLPI::Agent::Tools::Win32->use();

        my $key = getRegistryKey(
            path        => "HKEY_LOCAL_MACHINE/SOFTWARE/Open Source/",
            required    => [ qw/NodeId/ ],
            maxdepth    => 2,
            logger      => $params{logger}
        );

        # Any "Open Source" subkey holding a NodeId: the default agent uses "Mesh Agent", agents built
        # with MeshCentral agentCustomization use their serviceName (e.g. "AbundantLogicRemote").
        return $key && _meshSubkey($key);

    } elsif (OSNAME eq 'darwin') {
        return canRun('defaults') && Glob(
            "/Library/LaunchDaemons/meshagent*.plist"
        );
    }

    return unless OSNAME eq 'linux';
    return first { has_file($_) } @linuxPath;
}

sub doInventory {
    my (%params) = @_;

    my $inventory = $params{inventory};
    my $logger    = $params{logger};

    my $nodeId    = _getNodeId(logger => $logger)
        or return;

    $inventory->addEntry(
        section => 'REMOTE_MGMT',
        entry   => {
            ID   => $nodeId,
            TYPE => 'meshcentral'
        }
    );
}

sub _getNodeId {
    my (%params) = @_;

    return _winBased(%params) if OSNAME eq 'MSWin32';
    return _darwinBased(%params) if OSNAME eq 'darwin';
    return _linuxBased(%params);
}

sub _meshSubkey {
    my ($key) = @_;

    my @subkeys = grep {
        m{/$} && ref($key->{$_}) && !empty(GLPI::Agent::Tools::Win32::getRegistryKeyValue($key->{$_}, 'NodeId'))
    } keys(%{$key});

    # Prefer the default agent name, otherwise take the first customized one (sorted for stable results)
    return (grep { $_ eq 'Mesh Agent/' } @subkeys)[0] // (sort @subkeys)[0];
}

sub _winBased {
    my (%params) = @_;

    GLPI::Agent::Tools::Win32->use();

    my $key = getRegistryKey(
        path        => "HKEY_LOCAL_MACHINE/SOFTWARE/Open Source/",
        required    => [ qw/NodeId/ ],
        maxdepth    => 2,
        logger      => $params{logger}
    );
    return unless $key;

    my $subkey = _meshSubkey($key)
        or return;

    return GLPI::Agent::Tools::Win32::getRegistryKeyValue($key->{$subkey}, 'NodeId');
}

sub _linuxBased {
    my (%params) = @_;

    my $service = first { has_file($_) } qw{
        /etc/systemd/system/meshagent.service
        /usr/lib/systemd/system/meshagent.service
        /lib/systemd/system/meshagent.service
    };

    my $command = getFirstMatch(
        file    => $service,
        pattern => qr/Ex.*=(.*)\s\-/,
        logger  => $params{logger},
    );
    return if empty($command);

    return getFirstLine(
        command => "${command} -nodeid",
        logger  => $params{logger}
    );
}

sub _darwinBased {
    my (%params) = @_;

    return getFirstLine(
        command => "/usr/local/mesh_services/meshagent/meshagent_osx64 -nodeid",
        logger  => $params{logger}
    );
}

1;
