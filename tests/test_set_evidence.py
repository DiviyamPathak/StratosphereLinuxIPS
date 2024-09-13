import pytest
import datetime
from slips_files.core.structures.evidence import (
    ThreatLevel,
    EvidenceType,
    Direction,
)

from tests.module_factory import ModuleFactory


@pytest.mark.parametrize(
    "domain, age, stime, profileid, twid, uid, answers, expected_call_count",
    [
        # Testcase 1: Basic case with multiple answers
        (
            "example.com",
            10,
            "2023-05-06T12:00:00Z",
            "profile_192.168.0.1",
            "timewindow1",
            "unique_id",
            ["192.168.0.2", "192.168.0.3"],
            3,
        ),
        # Testcase 2: Single answer
        (
            "google.com",
            5,
            "2023-05-07T10:00:00Z",
            "profile_10.0.0.1",
            "timewindow2",
            "unique_id_2",
            ["172.217.160.142"],
            2,
        ),
        # Testcase 3: No answers
        (
            "test.com",
            2,
            "2023-05-08T14:00:00Z",
            "profile_172.16.0.1",
            "timewindow3",
            "unique_id_3",
            [],
            1,
        ),
    ],
)
def test_young_domain(
    domain,
    age,
    stime,
    profileid,
    twid,
    uid,
    answers,
    expected_call_count,
):
    """Testing the young_domain method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.young_domain(
        domain=domain,
        age=age,
        stime=stime,
        profileid=profileid,
        twid=twid,
        uid=uid,
        answers=answers,
    )

    assert set_ev.db.set_evidence.call_count == expected_call_count


@pytest.mark.parametrize(
    "cached_versions, current_versions, role, expected_description",
    [
        # Testcase1:Major Version Change
        (
            "7.2",
            "8.0",
            "SSH::CLIENT",
            "SSH client version changing from 7.2 to 8.0",
        ),
        # Testcase2:Minor Version Change
        (
            "2.2",
            "2.3",
            "SSH::SERVER",
            "SSH server version changing from 2.2 to 2.3",
        ),
        # Testcase3:Version Downgrade
        (
            "8.0",
            "7.2",
            "SSH::CLIENT",
            "SSH client version changing from 8.0 to 7.2",
        ),
        # Testcase4:Client and Server
        (
            "7.2",
            "8.0",
            "SSH::CLIENT",
            "SSH client version changing from 7.2 to 8.0",
        ),
        (
            "2.2",
            "3.1",
            "SSH::SERVER",
            "SSH server version changing from 2.2 to 3.1",
        ),
        # testcase5:Empty Version
        ("", "8.0", "SSH::CLIENT", "SSH client version changing from  to 8.0"),
        ("7.2", "", "SSH::SERVER", "SSH server version changing from 7.2 to "),
    ],
)
def test_multiple_ssh_versions(
    cached_versions, current_versions, role, expected_description
):
    """Test cases for multiple_ssh_versions with different versions,
    roles, and edge cases."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.multiple_ssh_versions(
        srcip="192.168.0.1",
        cached_versions=cached_versions,
        current_versions=current_versions,
        timestamp="2023-05-06T12:00:00Z",
        twid="timewindow2",
        uid=["unique_id1", "unique_id2"],
        role=role,
    )

    if expected_description is None:
        assert set_ev.db.set_evidence.call_count == 0
        return

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.MULTIPLE_SSH_VERSIONS
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert sorted(evidence.uid) == sorted(["unique_id1", "unique_id2"])
    assert evidence.description == expected_description


@pytest.mark.parametrize(
    "daddr, portproto,ip_outside_localnet, "
    "expected_attacker_direction, "
    "expected_victim_direction, "
    "expected_threat_level, expected_description",
    [
        # Testcase 1: src IP outside localnet
        (
            "10.0.0.1",
            "80",
            "srcip",
            Direction.SRC,
            Direction.DST,
            ThreatLevel.LOW,
            "A connection from a private IP (192.168.0.1) "
            "outside of the used local network 192.168.0.0/16."
            " To IP: 10.0.0.1 ",
        ),
        # Testcase 2: dst IP outside localnet, using ARP
        (
            "192.168.1.1",
            "arp",
            "dstip",
            Direction.DST,
            Direction.SRC,
            ThreatLevel.HIGH,
            "A connection to a private IP "
            "(192.168.1.1) outside of the used local network 192.168.0.0/16. "
            "From IP: 192.168.0.1 using ARP",
        ),
        # Testcase 3: dst IP outside localnet, using port
        (
            "192.168.1.2",
            "443",
            "dstip",
            Direction.DST,
            Direction.SRC,
            ThreatLevel.HIGH,
            "A connection to a private IP (192.168.1.2)"
            " outside of the used local network 192.168.0.0/16."
            " From IP: 192.168.0.1 on port: 443",
        ),
    ],
)
def test_different_localnet_usage(
    daddr,
    portproto,
    ip_outside_localnet,
    expected_attacker_direction,
    expected_victim_direction,
    expected_threat_level,
    expected_description,
):
    """Testing different scenarios for different_localnet_usage method:
    - src IP outside localnet
    - dst IP outside localnet using ARP
    - dst IP outside localnet using port
    """
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_local_network.return_value = "192.168.0.0/16"
    start_time = datetime.datetime(2023, 5, 6, 12, 0, 0)
    set_ev.db.get_slips_start_time.return_value = start_time.timestamp()
    set_ev.different_localnet_usage(
        daddr=daddr,
        portproto=portproto,
        profileid="profile_192.168.0.1",
        timestamp="2023-05-06T12:00:00Z",
        twid="timewindow3",
        uid="unique_id",
        ip_outside_localnet=ip_outside_localnet,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.DIFFERENT_LOCALNET
    assert evidence.attacker.direction == expected_attacker_direction
    assert evidence.victim.direction == expected_victim_direction
    assert evidence.threat_level == expected_threat_level
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 3
    assert evidence.uid == ["unique_id"]
    assert evidence.description == expected_description


def test_device_changing_ips():
    """Testing the device_changing_ips method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.device_changing_ips(
        smac="00:11:22:33:44:55",
        old_ip="10.0.0.1",
        profileid="profile_192.168.0.1",
        twid="timewindow4",
        uid="unique_id",
        timestamp="2023-05-06T12:00:00Z",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.DEVICE_CHANGING_IP
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 4
    assert evidence.uid == ["unique_id"]


def test_non_ssl_port_443_conn():
    """Testing the non_ssl_port_443_conn method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.non_ssl_port_443_conn(
        daddr="10.0.0.1",
        profileid="profile_192.168.0.1",
        timestamp="2023-05-06T12:00:00Z",
        twid="timewindow6",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.NON_SSL_PORT_443_CONNECTION
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == "10.0.0.1"
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 6
    assert evidence.uid == ["unique_id"]


@pytest.mark.parametrize(
    "org, daddr, expected_description",
    [
        # Testcase 1: Regular organization name
        (
            "example",
            "10.0.0.1",
            "Incompatible certificate CN to IP: 10.0.0.1 - "
            "Some Information - claiming to belong Example.",
        ),
        # Testcase 2: Organization name with spaces
        (
            "google llc",
            "8.8.8.8",
            "Incompatible certificate CN to IP: 8.8.8.8 - "
            "Some Information - claiming to belong Google llc.",
        ),
        # Testcase 3: Empty organization name
        (
            "",
            "192.168.1.1",
            "Incompatible certificate CN to IP: 192.168.1.1 - "
            "Some Information - claiming to belong .",
        ),
    ],
)
def test_incompatible_cn(org, daddr, expected_description):
    """Testing the incompatible_CN method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_ip_identification.return_value = "- Some Information -"
    set_ev.incompatible_cn(
        org=org,
        timestamp="2023-05-06T12:00:00Z",
        daddr=daddr,
        profileid="profile_192.168.0.1",
        twid="timewindow1",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.INCOMPATIBLE_CN
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == daddr
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 1
    assert evidence.uid == ["unique_id"]
    assert evidence.confidence == 0.9
    assert evidence.description == expected_description


@pytest.mark.parametrize(
    "nxdomains, expected_confidence",
    [  # Testcase 1: Exactly at the threshold
        (100, 1.00),
        # Testcase 2: Above the threshold
        (150, 1.50),
        # Testcase 3: Below the threshold
        (50, 0.5),
        # Testcase 4: Significantly above the threshold
        (300, 3.00),
    ],
)
def test_dga(nxdomains, expected_confidence):
    """Testing the DGA method with different nxdomains values."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.dga(
        nxdomains=nxdomains,
        stime="2023-05-06T12:00:00Z",
        profileid="profile_192.168.0.1",
        twid="timewindow2",
        uid=["unique_id"],
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.DGA_NXDOMAINS
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert evidence.uid == ["unique_id"]
    assert evidence.confidence == expected_confidence


@pytest.mark.parametrize(
    "bytes_downloaded, expected_response_body_len",
    [
        # Testcase 1: 1 MB download
        (1024 * 1024, 1.048576),
        # Testcase 2: 512 KB download
        (512 * 1024, 0.524288),
        # Testcase 3: 2.5 MB download
        (2.5 * 1024 * 1024, 2.62144),
    ],
)
def test_pastebin_download(bytes_downloaded, expected_response_body_len):
    """Testing the pastebin_download method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    result = set_ev.pastebin_download(
        bytes_downloaded=bytes_downloaded,
        timestamp="2023-05-06T12:00:00Z",
        profileid="profile_192.168.0.1",
        twid="timewindow2",
        uid="unique_id",
    )
    assert result is True

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.PASTEBIN_DOWNLOAD
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert evidence.uid == ["unique_id"]
    assert evidence.confidence == 1.0
    assert evidence.description == (
        f"A downloaded file from pastebin.com. "
        f"size: {expected_response_body_len} MBs"
    )


@pytest.mark.parametrize(
    "domain, timestamp, "
    "profileid, twid, uid, "
    "expected_attacker, expected_victim",
    [
        (  # Testcase 1: Regular domain
            "example.com",
            "2023-05-06T12:00:00Z",
            "profile_192.168.0.1",
            "timewindow1",
            "unique_id",
            "192.168.0.1",
            "example.com",
        ),
        (  # Testcase 2: Domain with hyphen
            "test-domain.com",
            "2023-05-07T12:00:00Z",
            "profile_10.0.0.1",
            "timewindow2",
            "unique_id_2",
            "10.0.0.1",
            "test-domain.com",
        ),
    ],
)
def test_dns_without_conn(
    domain,
    timestamp,
    profileid,
    twid,
    uid,
    expected_attacker,
    expected_victim,
):
    """Testing the dns_without_conn method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.dns_without_conn(
        domain=domain,
        timestamp=timestamp,
        profileid=profileid,
        twid=twid,
        uid=uid,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.DNS_WITHOUT_CONNECTION
    assert evidence.attacker.value == expected_attacker
    assert evidence.victim.value == expected_victim
    assert evidence.threat_level == ThreatLevel.LOW
    assert evidence.profile.ip == expected_attacker
    assert evidence.timewindow.number == int(twid.replace("timewindow", ""))
    assert evidence.uid == [uid]
    assert evidence.confidence == 0.8


def test_dns_arpa_scan():
    """Testing the dns_arpa_scan method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    result = set_ev.dns_arpa_scan(
        arpa_scan_threshold=150,
        stime="2023-05-06T12:00:00Z",
        profileid="profile_192.168.0.1",
        twid="timewindow2",
        uid=["unique_id"],
    )

    assert result is True
    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.DNS_ARPA_SCAN
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert evidence.uid == ["unique_id"]
    assert evidence.confidence == 0.7


@pytest.mark.parametrize(
    "time_difference_hours, expected_confidence",
    [  # Testcase1:Within the 5 hours
        (4, 0.1),
        # Testcase2:Outside the 5-hour window
        (6, 0.8),
    ],
)
def test_conn_without_dns(time_difference_hours, expected_confidence):
    """Testing the conn_without_dns method, including time-based confidence adjustment."""
    start_time = datetime.datetime.now() - datetime.timedelta(
        hours=time_difference_hours
    )
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_slips_start_time.return_value = start_time.timestamp()
    set_ev.conn_without_dns(
        daddr="10.0.0.1",
        timestamp=(start_time + datetime.timedelta(minutes=15)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        profileid="profile_192.168.0.1",
        twid="timewindow1",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.confidence == expected_confidence


@pytest.mark.parametrize(
    "daddr, dport, proto, expected_description",
    [
        # Testcase 1: Standard TCP connection to an unknown port
        (
            "10.0.0.1",
            12345,
            "tcp",
            "Connection to unknown destination port 12345/TCP "
            "destination IP 10.0.0.1. ",
        ),
        # Testcase 2: UDP connection to an unknown port
        (
            "192.168.1.100",
            56789,
            "udp",
            "Connection to unknown destination port 56789/UDP "
            "destination IP 192.168.1.100. ",
        ),
        # Testcase 3:  Edge case with port 0
        (
            "10.0.0.1",
            0,
            "tcp",
            "Connection to unknown destination port 0/TCP "
            "destination IP 10.0.0.1. ",
        ),
    ],
)
def test_unknown_port(daddr, dport, proto, expected_description):
    """Testing the unknown_port method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_ip_identification.return_value = ""
    set_ev.unknown_port(
        daddr=daddr,
        dport=dport,
        proto=proto,
        timestamp="2023-05-06T12:00:00Z",
        profileid="profile_192.168.0.1",
        twid="timewindow1",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.UNKNOWN_PORT
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == daddr
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 1
    assert evidence.uid == ["unique_id"]
    assert evidence.description == expected_description


def test_pw_guessing():
    """Testing the pw_guessing method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.pw_guessing(
        msg="192.168.0.1 appears to be guessing "
        "SSH passwords (seen in 30 connections)",
        timestamp="2023-05-06T12:00:00Z",
        twid="timewindow2",
        uid="unique_id",
        by="detection_model",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.PASSWORD_GUESSING
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert evidence.uid == ["unique_id"]


@pytest.mark.parametrize(
    "msg",
    [
        # Testcase 1: Standard message format
        "Seen at least 10 unique hosts scanned on 80/tcp",
        # Testcase 2: Different port and protocol
        "Seen at least 25 unique hosts scanned on 443/udp",
        # Testcase 3: Single host scanned
        "Seen at least 1 unique hosts scanned on 22/tcp",
        # Testcase 4: Large number of hosts scanned
        "Seen at least 1000 unique hosts scanned on 53/tcp",
    ],
)
def test_horizontal_portscan(msg, expected_conn_count):
    """Testing the horizontal_portscan method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.horizontal_portscan(
        msg=msg,
        timestamp="2023-05-06T12:00:00Z",
        profileid="profile_192.168.0.1",
        twid="timewindow3",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.HORIZONTAL_PORT_SCAN
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 3
    assert evidence.uid == ["unique_id"]


@pytest.mark.parametrize(
    "proto, daddr, dport, expected_description",
    [
        # Testcase 1: TCP connection to a private IP with a specific port
        (
            "tcp",
            "192.168.1.100",
            80,
            "Connecting to private IP: 192.168.1.100 on destination port: 80",
        ),
        # Testcase 2: UDP connection to a private IP with a specific port
        (
            "udp",
            "192.168.1.101",
            53,
            "Connecting to private IP: 192.168.1.101 on destination port: 53",
        ),
        # Testcase 3: ICMP connection to a private IP
        (
            "icmp",
            "192.168.1.102",
            "",
            "Connecting to private IP: 192.168.1.102 ",
        ),
        # Testcase 4: ARP connection to a private IP
        (
            "arp",
            "192.168.1.103",
            "",
            "Connecting to private IP: 192.168.1.103 ",
        ),
    ],
)
def test_conn_to_private_ip(proto, daddr, dport, expected_description):
    """Testing the conn_to_private_ip method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.conn_to_private_ip(
        proto=proto,
        daddr=daddr,
        dport=dport,
        saddr="192.168.0.1",
        twid="timewindow4",
        uid="unique_id",
        timestamp="2023-05-06T12:00:00Z",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.CONNECTION_TO_PRIVATE_IP
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == daddr
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 4
    assert evidence.uid == ["unique_id"]
    assert evidence.description == expected_description


def test_gre_tunnel():
    """Testing the GRE_tunnel method."""
    tunnel_info = {
        "profileid": "profile_192.168.0.1",
        "twid": "timewindow5",
        "flow": {
            "action": "TUNNEL",
            "daddr": "10.0.0.1",
            "starttime": "2023-05-06T12:00:00Z",
            "uid": "unique_id",
        },
    }
    set_evidence_helper = ModuleFactory().create_set_evidence_helper()
    set_evidence_helper.gre_tunnel(tunnel_info)

    assert set_evidence_helper.db.set_evidence.call_count == 1
    args, _ = set_evidence_helper.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.GRE_TUNNEL
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == "10.0.0.1"
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 5
    assert evidence.uid == ["unique_id"]


@pytest.mark.parametrize(
    "twid, saddr, "
    "daddr, size, "
    "uid, timestamp, by, "
    "expected_description",
    [
        (  # Test case 1: Basic successful SSH login
            "timewindow7",
            "192.168.0.1",
            "10.0.0.1",
            1024,
            "unique_id_1",
            "2023-05-06T12:00:00Z",
            "detection_model_1",
            "SSH successful to IP 10.0.0.1. "
            ". From IP 192.168.0.1. Sent bytes: 1024. "
            "Detection model detection_model_1. Confidence 0.8",
        ),
        (  # Test case 2: Different IPs, size, uid, timestamp, and detection model
            "timewindow8",
            "192.168.0.2",
            "10.0.0.2",
            2048,
            "unique_id_2",
            "2023-05-07T12:00:00Z",
            "detection_model_2",
            "SSH successful to IP 10.0.0.2. "
            ". From IP 192.168.0.2. "
            "Sent bytes: 2048. Detection model "
            "detection_model_2. Confidence 0.8",
        ),
        (  # Test case 3: Empty 'by' parameter
            "timewindow9",
            "192.168.0.3",
            "10.0.0.3",
            4096,
            "unique_id_3",
            "2023-05-08T12:00:00Z",
            "",
            "SSH successful to IP 10.0.0.3. "
            ". From IP 192.168.0.3. "
            "Sent bytes: 4096. Detection model . Confidence 0.8",
        ),
    ],
)
def test_ssh_successful(
    twid, saddr, daddr, size, uid, timestamp, by, expected_description
):
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_ip_identification.return_value = ""
    set_ev.ssh_successful(
        twid=twid,
        saddr=saddr,
        daddr=daddr,
        size=size,
        uid=uid,
        timestamp=timestamp,
        by=by,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.SSH_SUCCESSFUL
    assert evidence.attacker.value == saddr
    assert evidence.victim.value == daddr
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.confidence == 0.8
    assert evidence.profile.ip == saddr
    assert evidence.timewindow.number == int(twid.replace("timewindow", ""))
    assert evidence.uid == [uid]
    assert evidence.description == expected_description


def test_long_connection():
    """Testing the long_connection method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.long_connection(
        daddr="10.0.0.1",
        duration=7200,
        profileid="profile_192.168.0.1",
        twid="timewindow8",
        uid="unique_id",
        timestamp="2023-05-06T12:00:00Z",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.LONG_CONNECTION
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == "10.0.0.1"
    assert evidence.threat_level == ThreatLevel.LOW
    assert evidence.confidence == 0.08
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 8
    assert evidence.uid == ["unique_id"]


@pytest.mark.parametrize(
    "profileid, daddr, uid, "
    "timestamp, server_name, "
    "expected_attacker_ip_1, expected_profile_ip_1, "
    "expected_attacker_ip_2, expected_profile_ip_2",
    [
        # Testcase 1: Basic case with server name
        (
            "profile_192.168.0.1",
            "10.0.0.1",
            "unique_id_1",
            "2023-05-06T12:00:00Z",
            "example.com",
            "192.168.0.1",
            "192.168.0.1",
            "10.0.0.1",
            "192.168.0.1",
        ),
        # Testcase 2: Empty server name
        (
            "profile_192.168.0.3",
            "10.0.0.3",
            "unique_id_3",
            "2023-05-08T12:00:00Z",
            "",
            "192.168.0.3",
            "192.168.0.3",
            "10.0.0.3",
            "192.168.0.3",
        ),
        # Testcase 3: Attacker is destination IP
        (
            "profile_192.168.0.4",
            "10.0.0.4",
            "unique_id_4",
            "2023-05-09T12:00:00Z",
            "example.com",
            "192.168.0.4",
            "192.168.0.4",
            "10.0.0.4",
            "192.168.0.4",
        ),
    ],
)
def test_self_signed_certificates(
    profileid,
    daddr,
    uid,
    timestamp,
    server_name,
    expected_attacker_ip_1,
    expected_profile_ip_1,
    expected_attacker_ip_2,
    expected_profile_ip_2,
):
    """Testing the self_signed_certificates method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.self_signed_certificates(
        profileid=profileid,
        twid="timewindow1",
        daddr=daddr,
        uid=uid,
        timestamp=timestamp,
        server_name=server_name,
    )

    assert set_ev.db.set_evidence.call_count == 2
    call_args, _ = set_ev.db.set_evidence.call_args_list[0]
    evidence = call_args[0]
    assert evidence.evidence_type == EvidenceType.SELF_SIGNED_CERTIFICATE
    assert evidence.attacker.value == expected_attacker_ip_1
    assert evidence.threat_level == ThreatLevel.LOW
    assert evidence.confidence == 0.5
    assert evidence.profile.ip == expected_profile_ip_1
    assert evidence.timewindow.number == 1
    call_args, _ = set_ev.db.set_evidence.call_args_list[1]
    evidence = call_args[0]
    assert evidence.evidence_type == EvidenceType.SELF_SIGNED_CERTIFICATE
    assert evidence.attacker.value == expected_attacker_ip_2
    assert evidence.threat_level == ThreatLevel.LOW
    assert evidence.confidence == 0.5
    assert evidence.profile.ip == expected_profile_ip_2
    assert evidence.timewindow.number == 1


def test_multiple_reconnection_attempts():
    """Testing the multiple_reconnection_attempts method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.multiple_reconnection_attempts(
        profileid="profile_192.168.0.1",
        twid="timewindow2",
        daddr="10.0.0.1",
        uid=["unique_id1", "unique_id2"],
        timestamp="2023-05-06T12:00:00Z",
        reconnections=10,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert (
        evidence.evidence_type == EvidenceType.MULTIPLE_RECONNECTION_ATTEMPTS
    )
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == "10.0.0.1"
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.confidence == 0.5
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert sorted(evidence.uid) == sorted(["unique_id1", "unique_id2"])


@pytest.mark.parametrize(
    "profileid, attacker, "
    "victim, expected_attacker_direction, "
    "expected_victim_direction",
    [
        # Test case 1: profile_ip is attacker
        (
            "profile_192.168.0.1",
            "192.168.0.1",
            "192.168.0.2",
            Direction.SRC,
            Direction.DST,
        ),
        # Test case 2: profile_ip is victim
        (
            "profile_192.168.0.1",
            "192.168.0.2",
            "192.168.0.1",
            Direction.DST,
            Direction.SRC,
        ),
    ],
)
def test_connection_to_multiple_ports(
    profileid,
    attacker,
    victim,
    expected_attacker_direction,
    expected_victim_direction,
):
    """Testing the connection_to_multiple_ports method with parametrization.
    This test verifies the correct direction and profile_ip based on the input parameters.
    """
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.connection_to_multiple_ports(
        profileid=profileid,
        twid="timewindow3",
        uid=["unique_id"],
        timestamp="2023-05-06T12:00:00Z",
        dstports=[80, 8080, 8000],
        victim=victim,
        attacker=attacker,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.CONNECTION_TO_MULTIPLE_PORTS
    assert evidence.attacker.direction == expected_attacker_direction
    assert evidence.victim.direction == expected_victim_direction
    assert evidence.profile.ip == profileid.split("_")[-1]
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.confidence == 0.5
    assert evidence.timewindow.number == 3
    assert evidence.uid == ["unique_id"]


@pytest.mark.parametrize(
    "query, answer, entropy, daddr, profileid, twid, stime, uid",
    [
        # Testcase 1: Basic high entropy answer
        (
            "example.com",
            "aBcDeFgHiJkLmNoPqRsTuVwXyZ",
            4.5,
            "10.0.0.1",
            "profile_192.168.0.1",
            "timewindow4",
            "2023-05-06T12:00:00Z",
            "unique_id",
        ),
        # Testcase 2: Answer with special characters
        (
            "google.com",
            "aBc!@#$%^&*()_+=-`~",
            4.0,
            "10.0.0.3",
            "profile_192.168.0.3",
            "timewindow6",
            "2023-05-08T12:00:00Z",
            "unique_id_3",
        ),
    ],
)
def test_suspicious_dns_answer(
    query, answer, entropy, daddr, profileid, twid, stime, uid
):
    """Testing the suspicious_dns_answer method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.suspicious_dns_answer(
        query=query,
        answer=answer,
        entropy=entropy,
        daddr=daddr,
        profileid=profileid,
        twid=twid,
        stime=stime,
        uid=uid,
    )

    assert set_ev.db.set_evidence.call_count == 2
    args, _ = set_ev.db.set_evidence.call_args_list[0]
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.HIGH_ENTROPY_DNS_ANSWER
    assert evidence.attacker.value == daddr
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.confidence == 0.6
    assert evidence.profile.ip == daddr
    assert evidence.timewindow.number == int(twid.replace("timewindow", ""))
    assert evidence.uid == [uid]
    args, _ = set_ev.db.set_evidence.call_args_list[1]
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.HIGH_ENTROPY_DNS_ANSWER
    assert evidence.attacker.value == profileid.split("_")[-1]
    assert evidence.threat_level == ThreatLevel.LOW
    assert evidence.confidence == 0.6
    assert evidence.profile.ip == profileid.split("_")[-1]
    assert evidence.timewindow.number == int(twid.replace("timewindow", ""))
    assert evidence.uid == [uid]


@pytest.mark.parametrize(
    "query, answer, expected_description",
    [
        # Testcase 1: simple invalid resolution
        (
            "example.com",
            "127.0.0.1",
            "The DNS query example.com was resolved to 127.0.0.1",
        ),
        # Testcase 2: resolution to private IP
        (
            "google.com",
            "192.168.1.1",
            "The DNS query google.com was resolved to 192.168.1.1",
        ),
        # Testcase 3: empty answer
        ("test.com", "", "The DNS query test.com was resolved to "),
    ],
)
def test_invalid_dns_answer(query, answer, expected_description):
    """Testing the invalid_dns_answer method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.invalid_dns_answer(
        query=query,
        answer=answer,
        profileid="profile_192.168.0.1",
        twid="timewindow5",
        stime="2023-05-06T12:00:00Z",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.INVALID_DNS_RESOLUTION
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.confidence == 0.7
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 5
    assert evidence.uid == ["unique_id"]
    assert evidence.description == expected_description


@pytest.mark.parametrize(
    "profileid, attacker, victim, "
    "profile_ip, attacker_direction, victim_direction",
    [
        (  # Test case 1: profile_id is attacker
            "profile_192.168.0.1",
            "192.168.0.1",
            "10.0.0.1",
            "192.168.0.1",
            Direction.SRC,
            Direction.DST,
        ),
        (  # Test case 2: profile_id is victim
            "profile_10.0.0.1",
            "192.168.0.1",
            "10.0.0.1",
            "10.0.0.1",
            Direction.DST,
            Direction.SRC,
        ),
    ],
)
def test_for_port_0_connection(
    profileid,
    attacker,
    victim,
    profile_ip,
    attacker_direction,
    victim_direction,
):
    """Testing the for_port_0_connection method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.for_port_0_connection(
        saddr="192.168.0.1",
        daddr="10.0.0.1",
        sport=12345,
        dport=0,
        profileid=profileid,
        twid="timewindow6",
        uid="unique_id",
        timestamp="2023-05-06T12:00:00Z",
        victim=victim,
        attacker=attacker,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.PORT_0_CONNECTION
    assert evidence.attacker.value == attacker
    assert evidence.victim.value == victim
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.confidence == 0.8
    assert evidence.profile.ip == profile_ip
    assert evidence.timewindow.number == 6
    assert evidence.uid == ["unique_id"]
    assert evidence.attacker.direction == attacker_direction
    assert evidence.victim.direction == victim_direction


@pytest.mark.parametrize(
    "attacker_ip, threat_level, profile_ip",
    [  # Testcase1:daddr case
        ("10.0.0.1", ThreatLevel.HIGH, "10.0.0.1"),
        # Testcase2:saddr case
        ("192.168.0.1", ThreatLevel.LOW, "192.168.0.1"),
    ],
)
def test_malicious_ja3s(attacker_ip, threat_level, profile_ip):
    """Testing the malicious_ja3s method."""
    malicious_ja3_dict = {
        "ja3_hash_1": '{"threat_level": "high", '
        '"description": "Potential malware", "tags": "malware"}',
        "ja3_hash_2": '{"threat_level": "medium", '
        '"description": "Suspicious activity", "tags": "suspicious"}',
    }
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.malicious_ja3s(
        malicious_ja3_dict=malicious_ja3_dict,
        twid="timewindow9",
        uid="unique_id",
        timestamp="2023-05-06T12:00:00Z",
        saddr="192.168.0.1",
        daddr="10.0.0.1",
        ja3="ja3_hash_1",
    )

    assert set_ev.db.set_evidence.call_count == 2
    call_args_list = set_ev.db.set_evidence.call_args_list
    assert any(
        args[0].attacker.value == attacker_ip
        and args[0].threat_level == threat_level
        and args[0].profile.ip == profile_ip
        for args, _ in call_args_list
    )


@pytest.mark.parametrize(
    "attacker_ip, threat_level, description, tags",
    [
        (  # Test case 1: High threat level with description and tags
            "192.168.0.1",
            ThreatLevel.HIGH,
            "Potential malware",
            "malware",
        ),
        (  # Test case 2: Medium threat level with description and no tags
            "192.168.0.1",
            ThreatLevel.MEDIUM,
            "Suspicious activity",
            "",
        ),
    ],
)
def test_malicious_ja3(attacker_ip, threat_level, description, tags):
    """Testing the malicious_ja3 method."""
    malicious_ja3_dict = {
        "ja3_hash_8": '{"threat_level": "high", '
        '"description": "Potential malware", '
        '"tags": "malware"}',
        "ja3_hash_5": '{"threat_level": "medium", '
        '"description": "Suspicious activity", '
        '"tags": ""}',
    }
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_ip_identification.return_value = ""
    set_ev.malicious_ja3(
        malicious_ja3_dict=malicious_ja3_dict,
        twid="timewindow10",
        uid="unique_id",
        timestamp="2023-05-06T12:00:00Z",
        daddr="10.0.0.1",
        saddr=attacker_ip,
        ja3=f"ja3_hash_{int(threat_level.value * 10)}",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.MALICIOUS_JA3
    assert evidence.attacker.value == attacker_ip
    assert evidence.victim.value == "10.0.0.1"
    assert evidence.threat_level == threat_level
    assert evidence.profile.ip == attacker_ip
    assert evidence.timewindow.number == 10
    assert evidence.uid == ["unique_id"]
    expected_description_with_tags = (
        f"Malicious JA3: ja3_hash_{int(threat_level.value * 10)} "
        f"from source address {attacker_ip}  "
        f"description: {description}  tags: {tags}"
    )
    assert evidence.description == expected_description_with_tags


@pytest.mark.parametrize(
    "attacker_ip, threat_level, profile_ip",
    [
        # Testcase 1: Source IP as attacker
        ("192.168.0.1", ThreatLevel.INFO, "192.168.0.1"),
        # Testcase 2: Destination IP as attacker
        ("10.0.0.1", ThreatLevel.HIGH, "10.0.0.1"),
    ],
)
def test_data_exfiltration(attacker_ip, threat_level, profile_ip):
    """Testing the data_exfiltration method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.data_exfiltration(
        daddr="10.0.0.1",
        src_mbs=100.0,
        profileid="profile_192.168.0.1",
        twid="timewindow11",
        uid=["unique_id"],
        timestamp="2023-05-06T12:00:00Z",
    )

    assert set_ev.db.set_evidence.call_count == 2

    call_args_1, _ = set_ev.db.set_evidence.call_args_list[0]
    evidence_1 = call_args_1[0]
    assert evidence_1.attacker.value == "192.168.0.1"
    assert evidence_1.threat_level == ThreatLevel.INFO
    assert evidence_1.profile.ip == "192.168.0.1"
    call_args_2, _ = set_ev.db.set_evidence.call_args_list[1]
    evidence_2 = call_args_2[0]
    assert evidence_2.attacker.value == "10.0.0.1"
    assert evidence_2.threat_level == ThreatLevel.HIGH
    assert evidence_2.profile.ip == "10.0.0.1"


@pytest.mark.parametrize(
    "saddr, daddr, stime, twid, uid",
    [
        # Testcase 1: Normal bad SMTP login attempt
        (
            "192.168.0.1",
            "10.0.0.1",
            "2023-05-06T12:00:00Z",
            "timewindow12",
            "unique_id1",
        ),
        # Testcase 2:  Using IPv6 addresses
        (
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7335",
            "2023-05-08T15:45:00Z",
            "timewindow22",
            "unique_id3",
        ),
    ],
)
def test_bad_smtp_login(saddr, daddr, stime, twid, uid):
    """Testing the bad_smtp_login method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.bad_smtp_login(
        saddr=saddr,
        daddr=daddr,
        stime=stime,
        twid=twid,
        uid=uid,
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.BAD_SMTP_LOGIN
    assert evidence.attacker.value == saddr
    assert evidence.victim.value == daddr
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == saddr
    assert evidence.timewindow.number == int(twid.replace("timewindow", ""))
    assert evidence.uid == [uid]


@pytest.mark.parametrize(
    "flow, twid, uid, smtp_bruteforce_threshold",
    [
        # Testcase 1: Basic scenario with single uid
        (
            {
                "saddr": "192.168.0.1",
                "daddr": "10.0.0.1",
                "starttime": "2023-05-06T12:00:00Z",
            },
            "timewindow13",
            ["unique_id"],
            10,
        ),
        # Testcase 2: Multiple UIDs
        (
            {
                "saddr": "192.168.0.2",
                "daddr": "10.0.0.2",
                "starttime": "2023-05-07T12:00:00Z",
            },
            "timewindow14",
            ["uid1", "uid2", "uid3"],
            15,
        ),
    ],
)
def test_smtp_bruteforce(flow, twid, uid, smtp_bruteforce_threshold):
    """Testing the smtp_bruteforce method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.smtp_bruteforce(
        flow=flow,
        twid=twid,
        uid=uid,
        smtp_bruteforce_threshold=smtp_bruteforce_threshold,
    )
    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.SMTP_LOGIN_BRUTEFORCE
    assert evidence.attacker.value == flow["saddr"]
    assert evidence.victim.value == flow["daddr"]
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == flow["saddr"]
    assert evidence.timewindow.number == int(twid.replace("timewindow", ""))
    assert sorted(evidence.uid) == sorted(uid)


@pytest.mark.parametrize(
    "ssl_info, ssl_info_from_db, "
    "expected_threat_levels, expected_descriptions",
    [
        (
            {  # Test case 1: Basic malicious SSL with high threat level
                "flow": {
                    "starttime": "2023-05-06T12:00:00Z",
                    "daddr": "10.0.0.1",
                    "saddr": "192.168.0.1",
                    "uid": "unique_id1",
                },
                "twid": "timewindow14",
            },
            '{"tags": "malware", "description": "Potential malware", "threat_level": "high"}',
            [ThreatLevel.HIGH, ThreatLevel.LOW],
            [
                "Malicious SSL certificate to server 10.0.0.1. "
                "description: Potential malware malware  ",
                "Malicious SSL certificate to server 10.0.0.1. "
                "description: Potential malware malware  ",
            ],
        ),
        (
            {  # Test case 2: Malicious SSL with no tags
                "flow": {
                    "starttime": "2023-05-06T14:00:00Z",
                    "daddr": "10.0.0.3",
                    "saddr": "192.168.0.3",
                    "uid": "unique_id3",
                },
                "twid": "timewindow16",
            },
            '{"tags": "", "description": "No information available", "threat_level": "low"}',
            [ThreatLevel.LOW, ThreatLevel.LOW],
            [
                "Malicious SSL certificate to server 10.0.0.3. "
                "description: No information available   ",
                "Malicious SSL certificate to server 10.0.0.3. "
                "description: No information available   ",
            ],
        ),
    ],
)
def test_malicious_ssl(
    ssl_info,
    ssl_info_from_db,
    expected_threat_levels,
    expected_descriptions,
):
    """Testing the malicious_ssl method with parametrization
    and mocking for get_ip_identification."""

    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.db.get_ip_identification.return_value = ""
    set_ev.malicious_ssl(ssl_info, ssl_info_from_db)

    assert set_ev.db.set_evidence.call_count == 2
    for i, (args, _) in enumerate(set_ev.db.set_evidence.call_args_list):
        evidence = args[0]
        assert evidence.threat_level == expected_threat_levels[i]
        assert evidence.description == expected_descriptions[i]


@pytest.mark.parametrize(
    "attacker_ip, victim_ip, profile_ip",
    [
        # Test case 1: Destination IP is the attacker
        ("8.8.8.8", "192.168.0.1", "192.168.0.1"),
        # Test case 2: Source IP is the attacker
        ("192.168.0.1", "8.8.8.8", "8.8.8.8"),
    ],
)
def test_doh(attacker_ip, victim_ip, profile_ip):
    """Testing the doh method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.doh(
        daddr=attacker_ip,
        profileid=f"profile_{profile_ip}",
        twid="timewindow1",
        timestamp="2023-05-06T12:00:00Z",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.DIFFERENT_LOCALNET
    assert evidence.attacker.value == attacker_ip
    assert evidence.victim.value == victim_ip
    assert evidence.threat_level == ThreatLevel.INFO
    assert evidence.profile.ip == profile_ip
    assert evidence.timewindow.number == 1
    assert evidence.uid == ["unique_id"]


def test_non_http_port_80_conn():
    """Testing the non_http_port_80_conn method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.non_http_port_80_conn(
        daddr="10.0.0.1",
        profileid="profile_192.168.0.1",
        timestamp="2023-05-06T12:00:00Z",
        twid="timewindow2",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 2
    args, _ = set_ev.db.set_evidence.call_args_list[0]
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.NON_HTTP_PORT_80_CONNECTION
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == "10.0.0.1"
    assert evidence.threat_level == ThreatLevel.LOW
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 2
    assert evidence.uid == ["unique_id"]

    args, _ = set_ev.db.set_evidence.call_args_list[1]
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.NON_HTTP_PORT_80_CONNECTION
    assert evidence.attacker.value == "10.0.0.1"
    assert evidence.victim.value == "192.168.0.1"
    assert evidence.threat_level == ThreatLevel.MEDIUM
    assert evidence.profile.ip == "10.0.0.1"
    assert evidence.timewindow.number == 2
    assert evidence.uid == ["unique_id"]


def test_vertical_portscan():
    """Testing the vertical_portscan method."""
    set_ev = ModuleFactory().create_set_evidence_helper()
    set_ev.vertical_portscan(
        msg="192.168.0.1 has scanned at least 60 unique ports of host 192.168.0.2 in",
        scanning_ip="192.168.0.1",
        timestamp="2023-05-06T12:00:00Z",
        twid="timewindow1",
        uid="unique_id",
    )

    assert set_ev.db.set_evidence.call_count == 1
    args, _ = set_ev.db.set_evidence.call_args
    evidence = args[0]
    assert evidence.evidence_type == EvidenceType.VERTICAL_PORT_SCAN
    assert evidence.attacker.value == "192.168.0.1"
    assert evidence.victim.value == "192.168.0.2"
    assert evidence.threat_level == ThreatLevel.HIGH
    assert evidence.profile.ip == "192.168.0.1"
    assert evidence.timewindow.number == 1
    assert evidence.uid == ["unique_id"]
