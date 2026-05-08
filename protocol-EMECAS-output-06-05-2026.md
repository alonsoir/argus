## vagrant destroy -f
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant destroy -f
==> client: VM not created. Moving on...
==> defender: You assigned a static IP ending in ".1" or ":1" to this machine.
==> defender: This is very often used by the router and can cause the
==> defender: network to not work properly. If the network doesn't work
==> defender: properly, try changing this IP.
==> defender: Forcing shutdown of VM...
==> defender: Destroying VM and associated drives...

## vagrant up
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant up
Bringing machine 'defender' up with 'virtualbox' provider...
==> defender: You assigned a static IP ending in ".1" or ":1" to this machine.
==> defender: This is very often used by the router and can cause the
==> defender: network to not work properly. If the network doesn't work
==> defender: properly, try changing this IP.
==> defender: Importing base box 'debian/bookworm64'...
==> defender: Matching MAC address for NAT networking...
==> defender: You assigned a static IP ending in ".1" or ":1" to this machine.
==> defender: This is very often used by the router and can cause the
==> defender: network to not work properly. If the network doesn't work
==> defender: properly, try changing this IP.
==> defender: Checking if box 'debian/bookworm64' version '12.20240905.1' is up to date...
==> defender: Setting the name of the VM: ml-defender-gateway-lab
==> defender: Clearing any previously set network interfaces...
==> defender: Preparing network interfaces based on configuration...
defender: Adapter 1: nat
defender: Adapter 2: hostonly
defender: Adapter 3: intnet
==> defender: Forwarding ports...
defender: 5571 (guest) => 5571 (host) (adapter 1)
defender: 5572 (guest) => 5572 (host) (adapter 1)
defender: 2379 (guest) => 2379 (host) (adapter 1)
defender: 22 (guest) => 2222 (host) (adapter 1)
==> defender: Running 'pre-boot' VM customizations...
==> defender: Booting VM...
==> defender: Waiting for machine to boot. This may take a few minutes...
defender: SSH address: 127.0.0.1:2222
defender: SSH username: vagrant
defender: SSH auth method: private key
defender:
defender: Vagrant insecure key detected. Vagrant will automatically replace
defender: this with a newly generated keypair for better security.
defender:
defender: Inserting generated public key within guest...
defender: Removing insecure key from the guest if it's present...
defender: Key inserted! Disconnecting and reconnecting using new SSH key...
==> defender: Machine booted and ready!
==> defender: Checking for guest additions in VM...
defender: The guest additions on this VM do not match the installed version of
defender: VirtualBox! In most cases this is fine, but in rare cases it can
defender: prevent things such as shared folders from working properly. If you see
defender: shared folder errors, please make sure the guest additions within the
defender: virtual machine match the version of VirtualBox you have installed on
defender: your host and reload your VM.
defender:
defender: Guest Additions Version: 6.0.0 r127566
defender: VirtualBox Version: 7.2
==> defender: Configuring and enabling network interfaces...
==> defender: Mounting shared folders...
defender: /Users/aironman/CLionProjects/test-zeromq-docker => /vagrant
==> defender: Detected mount owner ID within mount options. (uid: 1000 guestpath: /vagrant)
==> defender: Detected mount group ID within mount options. (gid: 1000 guestpath: /vagrant)
==> defender: Running provisioner: shell...
defender: Running: inline script
defender: 🔧 Configurando interfaces de red para Dual-NIC testing...
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: iptables is already the newest version (1.8.9-2).
defender: nftables is already the newest version (1.0.6-2+deb12u2).
defender: iproute2 is already the newest version (6.1.0-3).
defender: The following additional packages will be installed:
defender:   libpcap0.8
defender: The following NEW packages will be installed:
defender:   ethtool libpcap0.8 tcpdump
defender: 0 upgraded, 3 newly installed, 0 to remove and 98 not upgraded.
defender: Need to get 820 kB of archives.
defender: After this operation, 2425 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 ethtool amd64 1:6.1-1 [197 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libpcap0.8 amd64 1.10.3-1 [157 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 tcpdump amd64 4.99.3-1 [467 kB]
defender: dpkg-preconfigure: unable to re-open stdin: No such file or directory
defender: Fetched 820 kB in 1s (987 kB/s)
defender: Selecting previously unselected package ethtool.
(Reading database ... 25481 files and directories currently installed.)
defender: Preparing to unpack .../ethtool_1%3a6.1-1_amd64.deb ...
defender: Unpacking ethtool (1:6.1-1) ...
defender: Selecting previously unselected package libpcap0.8:amd64.
defender: Preparing to unpack .../libpcap0.8_1.10.3-1_amd64.deb ...
defender: Unpacking libpcap0.8:amd64 (1.10.3-1) ...
defender: Selecting previously unselected package tcpdump.
defender: Preparing to unpack .../tcpdump_4.99.3-1_amd64.deb ...
defender: Unpacking tcpdump (4.99.3-1) ...
defender: Setting up libpcap0.8:amd64 (1.10.3-1) ...
defender: Setting up ethtool (1:6.1-1) ...
defender: Setting up tcpdump (4.99.3-1) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u8) ...
defender: 🌐 Activando IP forwarding para gateway mode...
defender: net.ipv4.ip_forward = 1
defender: net.ipv6.conf.all.forwarding = 1
defender: 🔧 Disabling rp_filter...
defender: net.ipv4.conf.all.rp_filter = 0
defender: net.ipv4.conf.eth1.rp_filter = 0
defender: net.ipv4.conf.eth2.rp_filter = 0
defender: 🔥 Configuring NAT/MASQUERADE...
defender: ═══════════════════════════════════════════════════════════
defender: 🎯 CONFIGURACIÓN DUAL-NIC ML DEFENDER
defender: ═══════════════════════════════════════════════════════════
defender: eth0: NAT (Vagrant management)
defender: eth1: 192.168.56.20 (WAN-facing, host-only) - Host-Based IDS
defender: eth2: 192.168.100.1 (LAN-facing, internal) - Gateway Mode
defender: IP Forwarding:  1
defender: rp_filter:  0
defender: Gateway Interface: eth2
defender: ═══════════════════════════════════════════════════════════
defender: 🔍 Configurando eth1 (WAN-facing, host-based)...
defender: ✅ eth1: Modo promiscuo ACTIVO (Host-Based IDS)
defender: 🔍 Configurando eth2 (LAN-facing, gateway mode)...
defender: ✅ eth2: Modo promiscuo ACTIVO (Gateway Mode)
defender:
defender: ═══════════════════════════════════════════════════════════
defender: ✅ CONFIGURACIÓN DE RED COMPLETADA
defender: ═══════════════════════════════════════════════════════════
defender: Interfaces disponibles:
defender: 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
defender: 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
defender:     inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic eth0
defender: 3: eth1: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
defender:     inet 192.168.56.20/24 brd 192.168.56.255 scope global eth1
defender: 4: eth2: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
defender:     inet 192.168.100.1/24 brd 192.168.100.255 scope global eth2
defender:
defender: ═══════════════════════════════════════════════════════════
defender:
==> defender: Running provisioner: all-dependencies (shell)...
defender: Running: script: all-dependencies
defender: ╔════════════════════════════════════════════════════════════╗
defender: ║  Installing ALL dependencies - Phase 2A (FAISS)           ║
defender: ╚════════════════════════════════════════════════════════════╝
defender: ++ echo ╔════════════════════════════════════════════════════════════╗
defender: ++ echo '║  Installing ALL dependencies - Phase 2A (FAISS)           ║'
defender: ++ echo ╚════════════════════════════════════════════════════════════╝
defender: ++ apt-get update
defender: Hit:1 https://security.debian.org/debian-security bookworm-security InRelease
defender: Hit:2 https://deb.debian.org/debian bookworm InRelease
defender: Hit:3 https://deb.debian.org/debian bookworm-updates InRelease
defender: Hit:4 https://deb.debian.org/debian bookworm-backports InRelease
defender: Reading package lists...
defender: ++ apt-get install -y build-essential git wget curl vim jq make rsync locales libc-bin file tmux xxd
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: file is already the newest version (1:5.44-3).
defender: The following additional packages will be installed:
defender:   binutils binutils-common binutils-x86-64-linux-gnu cpp cpp-12 dirmngr
defender:   dpkg-dev fakeroot fontconfig-config fonts-dejavu-core g++ g++-12 gcc gcc-12
defender:   gcc-12-base git-man gnupg gnupg-l10n gnupg-utils gpg gpg-agent
defender:   gpg-wks-client gpg-wks-server gpgconf gpgsm gpgv libabsl20220623
defender:   libalgorithm-diff-perl libalgorithm-diff-xs-perl libalgorithm-merge-perl
defender:   libaom3 libasan8 libassuan0 libatomic1 libavif15 libbinutils libc-dev-bin
defender:   libc-devtools libc-l10n libc6 libc6-dev libcc1-0 libcrypt-dev libctf-nobfd0
defender:   libctf0 libcurl3-gnutls libcurl4 libdav1d6 libde265-0 libdeflate0
defender:   libdpkg-perl liberror-perl libevent-core-2.1-7 libfakeroot
defender:   libfile-fcntllock-perl libfontconfig1 libgav1-1 libgcc-12-dev libgcc-s1
defender:   libgd3 libgomp1 libgpm2 libgprofng0 libheif1 libisl23 libitm1 libjbig0
defender:   libjpeg62-turbo libjq1 libksba8 liblerc4 liblsan0 libmpc3 libmpfr6 libnpth0
defender:   libnsl-dev libonig5 libquadmath0 librav1e0 libsodium23 libstdc++-12-dev
defender:   libstdc++6 libsvtav1enc1 libtiff6 libtirpc-dev libtsan2 libubsan1
defender:   libutempter0 libwebp7 libx11-6 libx11-data libx265-199 libxau6 libxcb1
defender:   libxdmcp6 libxpm4 libyuv0 linux-libc-dev manpages-dev patch pinentry-curses
defender:   rpcsvc-proto vim-common vim-runtime vim-tiny
defender: Suggested packages:
defender:   binutils-doc cpp-doc gcc-12-locales cpp-12-doc dbus-user-session
defender:   pinentry-gnome3 tor debian-keyring g++-multilib g++-12-multilib gcc-12-doc
defender:   gcc-multilib autoconf automake libtool flex bison gdb gcc-doc
defender:   gcc-12-multilib git-daemon-run | git-daemon-sysvinit git-doc git-email
defender:   git-gui gitk gitweb git-cvs git-mediawiki git-svn parcimonie xloadimage
defender:   scdaemon glibc-doc libnss-nis libnss-nisplus bzr libgd-tools gpm
defender:   libstdc++-12-doc make-doc ed diffutils-doc pinentry-doc python3-braceexpand
defender:   ctags vim-doc vim-scripts indent
defender: The following NEW packages will be installed:
defender:   binutils binutils-common binutils-x86-64-linux-gnu build-essential cpp
defender:   cpp-12 curl dirmngr dpkg-dev fakeroot fontconfig-config fonts-dejavu-core
defender:   g++ g++-12 gcc gcc-12 git git-man gnupg gnupg-l10n gnupg-utils gpg gpg-agent
defender:   gpg-wks-client gpg-wks-server gpgconf gpgsm jq libabsl20220623
defender:   libalgorithm-diff-perl libalgorithm-diff-xs-perl libalgorithm-merge-perl
defender:   libaom3 libasan8 libassuan0 libatomic1 libavif15 libbinutils libc-dev-bin
defender:   libc-devtools libc6-dev libcc1-0 libcrypt-dev libctf-nobfd0 libctf0 libcurl4
defender:   libdav1d6 libde265-0 libdeflate0 libdpkg-perl liberror-perl
defender:   libevent-core-2.1-7 libfakeroot libfile-fcntllock-perl libfontconfig1
defender:   libgav1-1 libgcc-12-dev libgd3 libgomp1 libgpm2 libgprofng0 libheif1
defender:   libisl23 libitm1 libjbig0 libjpeg62-turbo libjq1 libksba8 liblerc4 liblsan0
defender:   libmpc3 libmpfr6 libnpth0 libnsl-dev libonig5 libquadmath0 librav1e0
defender:   libsodium23 libstdc++-12-dev libsvtav1enc1 libtiff6 libtirpc-dev libtsan2
defender:   libubsan1 libutempter0 libwebp7 libx11-6 libx11-data libx265-199 libxau6
defender:   libxcb1 libxdmcp6 libxpm4 libyuv0 linux-libc-dev make manpages-dev patch
defender:   pinentry-curses rpcsvc-proto rsync tmux vim vim-runtime xxd
defender: The following packages will be upgraded:
defender:   gcc-12-base gpgv libc-bin libc-l10n libc6 libcurl3-gnutls libgcc-s1
defender:   libstdc++6 locales vim-common vim-tiny wget
defender: 12 upgraded, 105 newly installed, 0 to remove and 86 not upgraded.
defender: Need to get 120 MB of archives.
defender: After this operation, 429 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 gcc-12-base amd64 12.2.0-14+deb12u1 [37.6 kB]
defender: Get:2 https://security.debian.org/debian-security bookworm-security/main amd64 linux-libc-dev amd64 6.1.170-1 [2271 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libgcc-s1 amd64 12.2.0-14+deb12u1 [49.9 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 libstdc++6 amd64 12.2.0-14+deb12u1 [613 kB]
defender: Get:5 https://deb.debian.org/debian bookworm/main amd64 libc6 amd64 2.36-9+deb12u13 [2758 kB]
defender: Get:6 https://security.debian.org/debian-security bookworm-security/main amd64 libtiff6 amd64 4.5.0-6+deb12u4 [316 kB]
defender: Get:7 https://deb.debian.org/debian bookworm/main amd64 libc-bin amd64 2.36-9+deb12u13 [609 kB]
defender: Get:8 https://security.debian.org/debian-security bookworm-security/main amd64 libsodium23 amd64 1.0.18-1+deb12u1 [162 kB]
defender: Get:9 https://deb.debian.org/debian bookworm/main amd64 rsync amd64 3.2.7-1+deb12u4 [419 kB]
defender: Get:10 https://deb.debian.org/debian bookworm/main amd64 gpgv amd64 2.2.40-1.1+deb12u2 [649 kB]
defender: Get:11 https://deb.debian.org/debian bookworm/main amd64 vim-tiny amd64 2:9.0.1378-2+deb12u2 [720 kB]
defender: Get:12 https://deb.debian.org/debian bookworm/main amd64 vim-common all 2:9.0.1378-2+deb12u2 [125 kB]
defender: Get:13 https://deb.debian.org/debian bookworm/main amd64 libc-l10n all 2.36-9+deb12u13 [677 kB]
defender: Get:14 https://deb.debian.org/debian bookworm/main amd64 locales all 2.36-9+deb12u13 [3901 kB]
defender: Get:15 https://deb.debian.org/debian bookworm/main amd64 wget amd64 1.21.3-1+deb12u1 [937 kB]
defender: Get:16 https://deb.debian.org/debian bookworm/main amd64 binutils-common amd64 2.40-2 [2487 kB]
defender: Get:17 https://deb.debian.org/debian bookworm/main amd64 libbinutils amd64 2.40-2 [572 kB]
defender: Get:18 https://deb.debian.org/debian bookworm/main amd64 libctf-nobfd0 amd64 2.40-2 [153 kB]
defender: Get:19 https://deb.debian.org/debian bookworm/main amd64 libctf0 amd64 2.40-2 [89.8 kB]
defender: Get:20 https://deb.debian.org/debian bookworm/main amd64 libgprofng0 amd64 2.40-2 [812 kB]
defender: Get:21 https://deb.debian.org/debian bookworm/main amd64 binutils-x86-64-linux-gnu amd64 2.40-2 [2246 kB]
defender: Get:22 https://deb.debian.org/debian bookworm/main amd64 binutils amd64 2.40-2 [65.0 kB]
defender: Get:23 https://deb.debian.org/debian bookworm/main amd64 libc-dev-bin amd64 2.36-9+deb12u13 [47.4 kB]
defender: Get:24 https://deb.debian.org/debian bookworm/main amd64 libcrypt-dev amd64 1:4.4.33-2 [118 kB]
defender: Get:25 https://deb.debian.org/debian bookworm/main amd64 libtirpc-dev amd64 1.3.3+ds-1 [191 kB]
defender: Get:26 https://deb.debian.org/debian bookworm/main amd64 libnsl-dev amd64 1.3.0-2 [66.4 kB]
defender: Get:27 https://deb.debian.org/debian bookworm/main amd64 rpcsvc-proto amd64 1.4.3-1 [63.3 kB]
defender: Get:28 https://deb.debian.org/debian bookworm/main amd64 libc6-dev amd64 2.36-9+deb12u13 [1904 kB]
defender: Get:29 https://deb.debian.org/debian bookworm/main amd64 libisl23 amd64 0.25-1.1 [683 kB]
defender: Get:30 https://deb.debian.org/debian bookworm/main amd64 libmpfr6 amd64 4.2.0-1 [701 kB]
defender: Get:31 https://deb.debian.org/debian bookworm/main amd64 libmpc3 amd64 1.3.1-1 [51.5 kB]
defender: Get:32 https://deb.debian.org/debian bookworm/main amd64 cpp-12 amd64 12.2.0-14+deb12u1 [9768 kB]
defender: Get:33 https://deb.debian.org/debian bookworm/main amd64 cpp amd64 4:12.2.0-3 [6836 B]
defender: Get:34 https://deb.debian.org/debian bookworm/main amd64 libcc1-0 amd64 12.2.0-14+deb12u1 [41.7 kB]
defender: Get:35 https://deb.debian.org/debian bookworm/main amd64 libgomp1 amd64 12.2.0-14+deb12u1 [116 kB]
defender: Get:36 https://deb.debian.org/debian bookworm/main amd64 libitm1 amd64 12.2.0-14+deb12u1 [26.1 kB]
defender: Get:37 https://deb.debian.org/debian bookworm/main amd64 libatomic1 amd64 12.2.0-14+deb12u1 [9376 B]
defender: Get:38 https://deb.debian.org/debian bookworm/main amd64 libasan8 amd64 12.2.0-14+deb12u1 [2193 kB]
defender: Get:39 https://deb.debian.org/debian bookworm/main amd64 liblsan0 amd64 12.2.0-14+deb12u1 [969 kB]
defender: Get:40 https://deb.debian.org/debian bookworm/main amd64 libtsan2 amd64 12.2.0-14+deb12u1 [2197 kB]
defender: Get:41 https://deb.debian.org/debian bookworm/main amd64 libubsan1 amd64 12.2.0-14+deb12u1 [883 kB]
defender: Get:42 https://deb.debian.org/debian bookworm/main amd64 libquadmath0 amd64 12.2.0-14+deb12u1 [145 kB]
defender: Get:43 https://deb.debian.org/debian bookworm/main amd64 libgcc-12-dev amd64 12.2.0-14+deb12u1 [2437 kB]
defender: Get:44 https://deb.debian.org/debian bookworm/main amd64 gcc-12 amd64 12.2.0-14+deb12u1 [19.3 MB]
defender: Get:45 https://deb.debian.org/debian bookworm/main amd64 gcc amd64 4:12.2.0-3 [5216 B]
defender: Get:46 https://deb.debian.org/debian bookworm/main amd64 libstdc++-12-dev amd64 12.2.0-14+deb12u1 [2047 kB]
defender: Get:47 https://deb.debian.org/debian bookworm/main amd64 g++-12 amd64 12.2.0-14+deb12u1 [10.7 MB]
defender: Get:48 https://deb.debian.org/debian bookworm/main amd64 g++ amd64 4:12.2.0-3 [1356 B]
defender: Get:49 https://deb.debian.org/debian bookworm/main amd64 make amd64 4.3-4.1 [396 kB]
defender: Get:50 https://deb.debian.org/debian bookworm/main amd64 libdpkg-perl all 1.21.22 [603 kB]
defender: Get:51 https://deb.debian.org/debian bookworm/main amd64 patch amd64 2.7.6-7 [128 kB]
defender: Get:52 https://deb.debian.org/debian bookworm/main amd64 dpkg-dev all 1.21.22 [1353 kB]
defender: Get:53 https://deb.debian.org/debian bookworm/main amd64 build-essential amd64 12.9 [7704 B]
defender: Get:54 https://deb.debian.org/debian bookworm/main amd64 libcurl4 amd64 7.88.1-10+deb12u14 [392 kB]
defender: Get:55 https://deb.debian.org/debian bookworm/main amd64 curl amd64 7.88.1-10+deb12u14 [316 kB]
defender: Get:56 https://deb.debian.org/debian bookworm/main amd64 libassuan0 amd64 2.5.5-5 [48.5 kB]
defender: Get:57 https://deb.debian.org/debian bookworm/main amd64 gpgconf amd64 2.2.40-1.1+deb12u2 [565 kB]
defender: Get:58 https://deb.debian.org/debian bookworm/main amd64 libksba8 amd64 1.6.3-2 [128 kB]
defender: Get:59 https://deb.debian.org/debian bookworm/main amd64 libnpth0 amd64 1.6-3 [19.0 kB]
defender: Get:60 https://deb.debian.org/debian bookworm/main amd64 dirmngr amd64 2.2.40-1.1+deb12u2 [793 kB]
defender: Get:61 https://deb.debian.org/debian bookworm/main amd64 libfakeroot amd64 1.31-1.2 [28.3 kB]
defender: Get:62 https://deb.debian.org/debian bookworm/main amd64 fakeroot amd64 1.31-1.2 [66.9 kB]
defender: Get:63 https://deb.debian.org/debian bookworm/main amd64 fonts-dejavu-core all 2.37-6 [1068 kB]
defender: Get:64 https://deb.debian.org/debian bookworm/main amd64 fontconfig-config amd64 2.14.1-4 [315 kB]
defender: Get:65 https://deb.debian.org/debian bookworm/main amd64 libcurl3-gnutls amd64 7.88.1-10+deb12u14 [386 kB]
defender: Get:66 https://deb.debian.org/debian bookworm/main amd64 liberror-perl all 0.17029-2 [29.0 kB]
defender: Get:67 https://deb.debian.org/debian bookworm/main amd64 git-man all 1:2.39.5-0+deb12u3 [2053 kB]
defender: Get:68 https://deb.debian.org/debian bookworm/main amd64 git amd64 1:2.39.5-0+deb12u3 [7264 kB]
defender: Get:69 https://deb.debian.org/debian bookworm/main amd64 gnupg-l10n all 2.2.40-1.1+deb12u2 [1093 kB]
defender: Get:70 https://deb.debian.org/debian bookworm/main amd64 gnupg-utils amd64 2.2.40-1.1+deb12u2 [927 kB]
defender: Get:71 https://deb.debian.org/debian bookworm/main amd64 gpg amd64 2.2.40-1.1+deb12u2 [950 kB]
defender: Get:72 https://deb.debian.org/debian bookworm/main amd64 pinentry-curses amd64 1.2.1-1 [77.4 kB]
defender: Get:73 https://deb.debian.org/debian bookworm/main amd64 gpg-agent amd64 2.2.40-1.1+deb12u2 [695 kB]
defender: Get:74 https://deb.debian.org/debian bookworm/main amd64 gpg-wks-client amd64 2.2.40-1.1+deb12u2 [541 kB]
defender: Get:75 https://deb.debian.org/debian bookworm/main amd64 gpg-wks-server amd64 2.2.40-1.1+deb12u2 [531 kB]
defender: Get:76 https://deb.debian.org/debian bookworm/main amd64 gpgsm amd64 2.2.40-1.1+deb12u2 [671 kB]
defender: Get:77 https://deb.debian.org/debian bookworm/main amd64 gnupg all 2.2.40-1.1+deb12u2 [846 kB]
defender: Get:78 https://deb.debian.org/debian bookworm/main amd64 libonig5 amd64 6.9.8-1 [188 kB]
defender: Get:79 https://deb.debian.org/debian bookworm/main amd64 libjq1 amd64 1.6-2.1+deb12u1 [134 kB]
defender: Get:80 https://deb.debian.org/debian bookworm/main amd64 jq amd64 1.6-2.1+deb12u1 [63.7 kB]
defender: Get:81 https://deb.debian.org/debian bookworm/main amd64 libabsl20220623 amd64 20220623.1-1+deb12u2 [391 kB]
defender: Get:82 https://deb.debian.org/debian bookworm/main amd64 libalgorithm-diff-perl all 1.201-1 [43.3 kB]
defender: Get:83 https://deb.debian.org/debian bookworm/main amd64 libalgorithm-diff-xs-perl amd64 0.04-8+b1 [11.4 kB]
defender: Get:84 https://deb.debian.org/debian bookworm/main amd64 libalgorithm-merge-perl all 0.08-5 [11.8 kB]
defender: Get:85 https://deb.debian.org/debian bookworm/main amd64 libaom3 amd64 3.6.0-1+deb12u2 [1850 kB]
defender: Get:86 https://deb.debian.org/debian bookworm/main amd64 libdav1d6 amd64 1.0.0-2+deb12u1 [513 kB]
defender: Get:87 https://deb.debian.org/debian bookworm/main amd64 libgav1-1 amd64 0.18.0-1+b1 [332 kB]
defender: Get:88 https://deb.debian.org/debian bookworm/main amd64 librav1e0 amd64 0.5.1-6 [763 kB]
defender: Get:89 https://deb.debian.org/debian bookworm/main amd64 libsvtav1enc1 amd64 1.4.1+dfsg-1 [2121 kB]
defender: Get:90 https://deb.debian.org/debian bookworm/main amd64 libjpeg62-turbo amd64 1:2.1.5-2 [166 kB]
defender: Get:91 https://deb.debian.org/debian bookworm/main amd64 libyuv0 amd64 0.0~git20230123.b2528b0-1 [168 kB]
defender: Get:92 https://deb.debian.org/debian bookworm/main amd64 libavif15 amd64 0.11.1-1+deb12u1 [94.4 kB]
defender: Get:93 https://deb.debian.org/debian bookworm/main amd64 libfontconfig1 amd64 2.14.1-4 [386 kB]
defender: Get:94 https://deb.debian.org/debian bookworm/main amd64 libde265-0 amd64 1.0.11-1+deb12u2 [185 kB]
defender: Get:95 https://deb.debian.org/debian bookworm/main amd64 libx265-199 amd64 3.5-2+b1 [1150 kB]
defender: Get:96 https://deb.debian.org/debian bookworm/main amd64 libheif1 amd64 1.15.1-1+deb12u1 [215 kB]
defender: Get:97 https://deb.debian.org/debian bookworm/main amd64 libdeflate0 amd64 1.14-1 [61.4 kB]
defender: Get:98 https://deb.debian.org/debian bookworm/main amd64 libjbig0 amd64 2.1-6.1 [31.7 kB]
defender: Get:99 https://deb.debian.org/debian bookworm/main amd64 liblerc4 amd64 4.0.0+ds-2 [170 kB]
defender: Get:100 https://deb.debian.org/debian bookworm/main amd64 libwebp7 amd64 1.2.4-0.2+deb12u1 [286 kB]
defender: Get:101 https://deb.debian.org/debian bookworm/main amd64 libxau6 amd64 1:1.0.9-1 [19.7 kB]
defender: Get:102 https://deb.debian.org/debian bookworm/main amd64 libxdmcp6 amd64 1:1.1.2-3 [26.3 kB]
defender: Get:103 https://deb.debian.org/debian bookworm/main amd64 libxcb1 amd64 1.15-1 [144 kB]
defender: Get:104 https://deb.debian.org/debian bookworm/main amd64 libx11-data all 2:1.8.4-2+deb12u2 [292 kB]
defender: Get:105 https://deb.debian.org/debian bookworm/main amd64 libx11-6 amd64 2:1.8.4-2+deb12u2 [760 kB]
defender: Get:106 https://deb.debian.org/debian bookworm/main amd64 libxpm4 amd64 1:3.5.12-1.1+deb12u1 [48.6 kB]
defender: Get:107 https://deb.debian.org/debian bookworm/main amd64 libgd3 amd64 2.3.3-9 [124 kB]
defender: Get:108 https://deb.debian.org/debian bookworm/main amd64 libc-devtools amd64 2.36-9+deb12u13 [55.0 kB]
defender: Get:109 https://deb.debian.org/debian bookworm/main amd64 libevent-core-2.1-7 amd64 2.1.12-stable-8 [131 kB]
defender: Get:110 https://deb.debian.org/debian bookworm/main amd64 libfile-fcntllock-perl amd64 0.22-4+b1 [34.8 kB]
defender: Get:111 https://deb.debian.org/debian bookworm/main amd64 libgpm2 amd64 1.20.7-10+b1 [14.2 kB]
defender: Get:112 https://deb.debian.org/debian bookworm/main amd64 libutempter0 amd64 1.2.1-3 [8960 B]
defender: Get:113 https://deb.debian.org/debian bookworm/main amd64 manpages-dev all 6.03-2 [2030 kB]
defender: Get:114 https://deb.debian.org/debian bookworm/main amd64 tmux amd64 3.3a-3 [455 kB]
defender: Get:115 https://deb.debian.org/debian bookworm/main amd64 vim-runtime all 2:9.0.1378-2+deb12u2 [7027 kB]
defender: Get:116 https://deb.debian.org/debian bookworm/main amd64 vim amd64 2:9.0.1378-2+deb12u2 [1568 kB]
defender: Get:117 https://deb.debian.org/debian bookworm/main amd64 xxd amd64 2:9.0.1378-2+deb12u2 [84.1 kB]
defender: apt-listchanges: Reading changelogs...
defender: Preconfiguring packages ...
defender: Fetched 120 MB in 1min 12s (1667 kB/s)
(Reading database ... 25518 files and directories currently installed.)
defender: Preparing to unpack .../gcc-12-base_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking gcc-12-base:amd64 (12.2.0-14+deb12u1) over (12.2.0-14) ...
defender: Setting up gcc-12-base:amd64 (12.2.0-14+deb12u1) ...
(Reading database ... 25518 files and directories currently installed.)
defender: Preparing to unpack .../libgcc-s1_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libgcc-s1:amd64 (12.2.0-14+deb12u1) over (12.2.0-14) ...
defender: Setting up libgcc-s1:amd64 (12.2.0-14+deb12u1) ...
(Reading database ... 25518 files and directories currently installed.)
defender: Preparing to unpack .../libstdc++6_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libstdc++6:amd64 (12.2.0-14+deb12u1) over (12.2.0-14) ...
defender: Setting up libstdc++6:amd64 (12.2.0-14+deb12u1) ...
(Reading database ... 25518 files and directories currently installed.)
defender: Preparing to unpack .../libc6_2.36-9+deb12u13_amd64.deb ...
defender: Unpacking libc6:amd64 (2.36-9+deb12u13) over (2.36-9+deb12u8) ...
defender: Setting up libc6:amd64 (2.36-9+deb12u13) ...
(Reading database ... 25518 files and directories currently installed.)
defender: Preparing to unpack .../libc-bin_2.36-9+deb12u13_amd64.deb ...
defender: Unpacking libc-bin (2.36-9+deb12u13) over (2.36-9+deb12u8) ...
defender: Setting up libc-bin (2.36-9+deb12u13) ...
defender: Selecting previously unselected package rsync.
(Reading database ... 25518 files and directories currently installed.)
defender: Preparing to unpack .../rsync_3.2.7-1+deb12u4_amd64.deb ...
defender: Unpacking rsync (3.2.7-1+deb12u4) ...
defender: Preparing to unpack .../gpgv_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpgv (2.2.40-1.1+deb12u2) over (2.2.40-1.1) ...
defender: Setting up gpgv (2.2.40-1.1+deb12u2) ...
(Reading database ... 25552 files and directories currently installed.)
defender: Preparing to unpack .../000-vim-tiny_2%3a9.0.1378-2+deb12u2_amd64.deb ...
defender: Unpacking vim-tiny (2:9.0.1378-2+deb12u2) over (2:9.0.1378-2) ...
defender: Preparing to unpack .../001-vim-common_2%3a9.0.1378-2+deb12u2_all.deb ...
defender: Unpacking vim-common (2:9.0.1378-2+deb12u2) over (2:9.0.1378-2) ...
defender: Preparing to unpack .../002-libc-l10n_2.36-9+deb12u13_all.deb ...
defender: Unpacking libc-l10n (2.36-9+deb12u13) over (2.36-9+deb12u8) ...
defender: Preparing to unpack .../003-locales_2.36-9+deb12u13_all.deb ...
defender: Unpacking locales (2.36-9+deb12u13) over (2.36-9+deb12u8) ...
defender: Preparing to unpack .../004-wget_1.21.3-1+deb12u1_amd64.deb ...
defender: Unpacking wget (1.21.3-1+deb12u1) over (1.21.3-1+b2) ...
defender: Selecting previously unselected package binutils-common:amd64.
defender: Preparing to unpack .../005-binutils-common_2.40-2_amd64.deb ...
defender: Unpacking binutils-common:amd64 (2.40-2) ...
defender: Selecting previously unselected package libbinutils:amd64.
defender: Preparing to unpack .../006-libbinutils_2.40-2_amd64.deb ...
defender: Unpacking libbinutils:amd64 (2.40-2) ...
defender: Selecting previously unselected package libctf-nobfd0:amd64.
defender: Preparing to unpack .../007-libctf-nobfd0_2.40-2_amd64.deb ...
defender: Unpacking libctf-nobfd0:amd64 (2.40-2) ...
defender: Selecting previously unselected package libctf0:amd64.
defender: Preparing to unpack .../008-libctf0_2.40-2_amd64.deb ...
defender: Unpacking libctf0:amd64 (2.40-2) ...
defender: Selecting previously unselected package libgprofng0:amd64.
defender: Preparing to unpack .../009-libgprofng0_2.40-2_amd64.deb ...
defender: Unpacking libgprofng0:amd64 (2.40-2) ...
defender: Selecting previously unselected package binutils-x86-64-linux-gnu.
defender: Preparing to unpack .../010-binutils-x86-64-linux-gnu_2.40-2_amd64.deb ...
defender: Unpacking binutils-x86-64-linux-gnu (2.40-2) ...
defender: Selecting previously unselected package binutils.
defender: Preparing to unpack .../011-binutils_2.40-2_amd64.deb ...
defender: Unpacking binutils (2.40-2) ...
defender: Selecting previously unselected package libc-dev-bin.
defender: Preparing to unpack .../012-libc-dev-bin_2.36-9+deb12u13_amd64.deb ...
defender: Unpacking libc-dev-bin (2.36-9+deb12u13) ...
defender: Selecting previously unselected package linux-libc-dev:amd64.
defender: Preparing to unpack .../013-linux-libc-dev_6.1.170-1_amd64.deb ...
defender: Unpacking linux-libc-dev:amd64 (6.1.170-1) ...
defender: Selecting previously unselected package libcrypt-dev:amd64.
defender: Preparing to unpack .../014-libcrypt-dev_1%3a4.4.33-2_amd64.deb ...
defender: Unpacking libcrypt-dev:amd64 (1:4.4.33-2) ...
defender: Selecting previously unselected package libtirpc-dev:amd64.
defender: Preparing to unpack .../015-libtirpc-dev_1.3.3+ds-1_amd64.deb ...
defender: Unpacking libtirpc-dev:amd64 (1.3.3+ds-1) ...
defender: Selecting previously unselected package libnsl-dev:amd64.
defender: Preparing to unpack .../016-libnsl-dev_1.3.0-2_amd64.deb ...
defender: Unpacking libnsl-dev:amd64 (1.3.0-2) ...
defender: Selecting previously unselected package rpcsvc-proto.
defender: Preparing to unpack .../017-rpcsvc-proto_1.4.3-1_amd64.deb ...
defender: Unpacking rpcsvc-proto (1.4.3-1) ...
defender: Selecting previously unselected package libc6-dev:amd64.
defender: Preparing to unpack .../018-libc6-dev_2.36-9+deb12u13_amd64.deb ...
defender: Unpacking libc6-dev:amd64 (2.36-9+deb12u13) ...
defender: Selecting previously unselected package libisl23:amd64.
defender: Preparing to unpack .../019-libisl23_0.25-1.1_amd64.deb ...
defender: Unpacking libisl23:amd64 (0.25-1.1) ...
defender: Selecting previously unselected package libmpfr6:amd64.
defender: Preparing to unpack .../020-libmpfr6_4.2.0-1_amd64.deb ...
defender: Unpacking libmpfr6:amd64 (4.2.0-1) ...
defender: Selecting previously unselected package libmpc3:amd64.
defender: Preparing to unpack .../021-libmpc3_1.3.1-1_amd64.deb ...
defender: Unpacking libmpc3:amd64 (1.3.1-1) ...
defender: Selecting previously unselected package cpp-12.
defender: Preparing to unpack .../022-cpp-12_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking cpp-12 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package cpp.
defender: Preparing to unpack .../023-cpp_4%3a12.2.0-3_amd64.deb ...
defender: Unpacking cpp (4:12.2.0-3) ...
defender: Selecting previously unselected package libcc1-0:amd64.
defender: Preparing to unpack .../024-libcc1-0_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libcc1-0:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libgomp1:amd64.
defender: Preparing to unpack .../025-libgomp1_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libgomp1:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libitm1:amd64.
defender: Preparing to unpack .../026-libitm1_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libitm1:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libatomic1:amd64.
defender: Preparing to unpack .../027-libatomic1_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libatomic1:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libasan8:amd64.
defender: Preparing to unpack .../028-libasan8_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libasan8:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package liblsan0:amd64.
defender: Preparing to unpack .../029-liblsan0_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking liblsan0:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libtsan2:amd64.
defender: Preparing to unpack .../030-libtsan2_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libtsan2:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libubsan1:amd64.
defender: Preparing to unpack .../031-libubsan1_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libubsan1:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libquadmath0:amd64.
defender: Preparing to unpack .../032-libquadmath0_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libquadmath0:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libgcc-12-dev:amd64.
defender: Preparing to unpack .../033-libgcc-12-dev_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libgcc-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package gcc-12.
defender: Preparing to unpack .../034-gcc-12_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking gcc-12 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package gcc.
defender: Preparing to unpack .../035-gcc_4%3a12.2.0-3_amd64.deb ...
defender: Unpacking gcc (4:12.2.0-3) ...
defender: Selecting previously unselected package libstdc++-12-dev:amd64.
defender: Preparing to unpack .../036-libstdc++-12-dev_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libstdc++-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package g++-12.
defender: Preparing to unpack .../037-g++-12_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking g++-12 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package g++.
defender: Preparing to unpack .../038-g++_4%3a12.2.0-3_amd64.deb ...
defender: Unpacking g++ (4:12.2.0-3) ...
defender: Selecting previously unselected package make.
defender: Preparing to unpack .../039-make_4.3-4.1_amd64.deb ...
defender: Unpacking make (4.3-4.1) ...
defender: Selecting previously unselected package libdpkg-perl.
defender: Preparing to unpack .../040-libdpkg-perl_1.21.22_all.deb ...
defender: Unpacking libdpkg-perl (1.21.22) ...
defender: Selecting previously unselected package patch.
defender: Preparing to unpack .../041-patch_2.7.6-7_amd64.deb ...
defender: Unpacking patch (2.7.6-7) ...
defender: Selecting previously unselected package dpkg-dev.
defender: Preparing to unpack .../042-dpkg-dev_1.21.22_all.deb ...
defender: Unpacking dpkg-dev (1.21.22) ...
defender: Selecting previously unselected package build-essential.
defender: Preparing to unpack .../043-build-essential_12.9_amd64.deb ...
defender: Unpacking build-essential (12.9) ...
defender: Selecting previously unselected package libcurl4:amd64.
defender: Preparing to unpack .../044-libcurl4_7.88.1-10+deb12u14_amd64.deb ...
defender: Unpacking libcurl4:amd64 (7.88.1-10+deb12u14) ...
defender: Selecting previously unselected package curl.
defender: Preparing to unpack .../045-curl_7.88.1-10+deb12u14_amd64.deb ...
defender: Unpacking curl (7.88.1-10+deb12u14) ...
defender: Selecting previously unselected package libassuan0:amd64.
defender: Preparing to unpack .../046-libassuan0_2.5.5-5_amd64.deb ...
defender: Unpacking libassuan0:amd64 (2.5.5-5) ...
defender: Selecting previously unselected package gpgconf.
defender: Preparing to unpack .../047-gpgconf_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpgconf (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package libksba8:amd64.
defender: Preparing to unpack .../048-libksba8_1.6.3-2_amd64.deb ...
defender: Unpacking libksba8:amd64 (1.6.3-2) ...
defender: Selecting previously unselected package libnpth0:amd64.
defender: Preparing to unpack .../049-libnpth0_1.6-3_amd64.deb ...
defender: Unpacking libnpth0:amd64 (1.6-3) ...
defender: Selecting previously unselected package dirmngr.
defender: Preparing to unpack .../050-dirmngr_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking dirmngr (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package libfakeroot:amd64.
defender: Preparing to unpack .../051-libfakeroot_1.31-1.2_amd64.deb ...
defender: Unpacking libfakeroot:amd64 (1.31-1.2) ...
defender: Selecting previously unselected package fakeroot.
defender: Preparing to unpack .../052-fakeroot_1.31-1.2_amd64.deb ...
defender: Unpacking fakeroot (1.31-1.2) ...
defender: Selecting previously unselected package fonts-dejavu-core.
defender: Preparing to unpack .../053-fonts-dejavu-core_2.37-6_all.deb ...
defender: Unpacking fonts-dejavu-core (2.37-6) ...
defender: Selecting previously unselected package fontconfig-config.
defender: Preparing to unpack .../054-fontconfig-config_2.14.1-4_amd64.deb ...
defender: Unpacking fontconfig-config (2.14.1-4) ...
defender: Preparing to unpack .../055-libcurl3-gnutls_7.88.1-10+deb12u14_amd64.deb ...
defender: Unpacking libcurl3-gnutls:amd64 (7.88.1-10+deb12u14) over (7.88.1-10+deb12u7) ...
defender: Selecting previously unselected package liberror-perl.
defender: Preparing to unpack .../056-liberror-perl_0.17029-2_all.deb ...
defender: Unpacking liberror-perl (0.17029-2) ...
defender: Selecting previously unselected package git-man.
defender: Preparing to unpack .../057-git-man_1%3a2.39.5-0+deb12u3_all.deb ...
defender: Unpacking git-man (1:2.39.5-0+deb12u3) ...
defender: Selecting previously unselected package git.
defender: Preparing to unpack .../058-git_1%3a2.39.5-0+deb12u3_amd64.deb ...
defender: Unpacking git (1:2.39.5-0+deb12u3) ...
defender: Selecting previously unselected package gnupg-l10n.
defender: Preparing to unpack .../059-gnupg-l10n_2.2.40-1.1+deb12u2_all.deb ...
defender: Unpacking gnupg-l10n (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package gnupg-utils.
defender: Preparing to unpack .../060-gnupg-utils_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gnupg-utils (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package gpg.
defender: Preparing to unpack .../061-gpg_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpg (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package pinentry-curses.
defender: Preparing to unpack .../062-pinentry-curses_1.2.1-1_amd64.deb ...
defender: Unpacking pinentry-curses (1.2.1-1) ...
defender: Selecting previously unselected package gpg-agent.
defender: Preparing to unpack .../063-gpg-agent_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpg-agent (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package gpg-wks-client.
defender: Preparing to unpack .../064-gpg-wks-client_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpg-wks-client (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package gpg-wks-server.
defender: Preparing to unpack .../065-gpg-wks-server_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpg-wks-server (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package gpgsm.
defender: Preparing to unpack .../066-gpgsm_2.2.40-1.1+deb12u2_amd64.deb ...
defender: Unpacking gpgsm (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package gnupg.
defender: Preparing to unpack .../067-gnupg_2.2.40-1.1+deb12u2_all.deb ...
defender: Unpacking gnupg (2.2.40-1.1+deb12u2) ...
defender: Selecting previously unselected package libonig5:amd64.
defender: Preparing to unpack .../068-libonig5_6.9.8-1_amd64.deb ...
defender: Unpacking libonig5:amd64 (6.9.8-1) ...
defender: Selecting previously unselected package libjq1:amd64.
defender: Preparing to unpack .../069-libjq1_1.6-2.1+deb12u1_amd64.deb ...
defender: Unpacking libjq1:amd64 (1.6-2.1+deb12u1) ...
defender: Selecting previously unselected package jq.
defender: Preparing to unpack .../070-jq_1.6-2.1+deb12u1_amd64.deb ...
defender: Unpacking jq (1.6-2.1+deb12u1) ...
defender: Selecting previously unselected package libabsl20220623:amd64.
defender: Preparing to unpack .../071-libabsl20220623_20220623.1-1+deb12u2_amd64.deb ...
defender: Unpacking libabsl20220623:amd64 (20220623.1-1+deb12u2) ...
defender: Selecting previously unselected package libalgorithm-diff-perl.
defender: Preparing to unpack .../072-libalgorithm-diff-perl_1.201-1_all.deb ...
defender: Unpacking libalgorithm-diff-perl (1.201-1) ...
defender: Selecting previously unselected package libalgorithm-diff-xs-perl:amd64.
defender: Preparing to unpack .../073-libalgorithm-diff-xs-perl_0.04-8+b1_amd64.deb ...
defender: Unpacking libalgorithm-diff-xs-perl:amd64 (0.04-8+b1) ...
defender: Selecting previously unselected package libalgorithm-merge-perl.
defender: Preparing to unpack .../074-libalgorithm-merge-perl_0.08-5_all.deb ...
defender: Unpacking libalgorithm-merge-perl (0.08-5) ...
defender: Selecting previously unselected package libaom3:amd64.
defender: Preparing to unpack .../075-libaom3_3.6.0-1+deb12u2_amd64.deb ...
defender: Unpacking libaom3:amd64 (3.6.0-1+deb12u2) ...
defender: Selecting previously unselected package libdav1d6:amd64.
defender: Preparing to unpack .../076-libdav1d6_1.0.0-2+deb12u1_amd64.deb ...
defender: Unpacking libdav1d6:amd64 (1.0.0-2+deb12u1) ...
defender: Selecting previously unselected package libgav1-1:amd64.
defender: Preparing to unpack .../077-libgav1-1_0.18.0-1+b1_amd64.deb ...
defender: Unpacking libgav1-1:amd64 (0.18.0-1+b1) ...
defender: Selecting previously unselected package librav1e0:amd64.
defender: Preparing to unpack .../078-librav1e0_0.5.1-6_amd64.deb ...
defender: Unpacking librav1e0:amd64 (0.5.1-6) ...
defender: Selecting previously unselected package libsvtav1enc1:amd64.
defender: Preparing to unpack .../079-libsvtav1enc1_1.4.1+dfsg-1_amd64.deb ...
defender: Unpacking libsvtav1enc1:amd64 (1.4.1+dfsg-1) ...
defender: Selecting previously unselected package libjpeg62-turbo:amd64.
defender: Preparing to unpack .../080-libjpeg62-turbo_1%3a2.1.5-2_amd64.deb ...
defender: Unpacking libjpeg62-turbo:amd64 (1:2.1.5-2) ...
defender: Selecting previously unselected package libyuv0:amd64.
defender: Preparing to unpack .../081-libyuv0_0.0~git20230123.b2528b0-1_amd64.deb ...
defender: Unpacking libyuv0:amd64 (0.0~git20230123.b2528b0-1) ...
defender: Selecting previously unselected package libavif15:amd64.
defender: Preparing to unpack .../082-libavif15_0.11.1-1+deb12u1_amd64.deb ...
defender: Unpacking libavif15:amd64 (0.11.1-1+deb12u1) ...
defender: Selecting previously unselected package libfontconfig1:amd64.
defender: Preparing to unpack .../083-libfontconfig1_2.14.1-4_amd64.deb ...
defender: Unpacking libfontconfig1:amd64 (2.14.1-4) ...
defender: Selecting previously unselected package libde265-0:amd64.
defender: Preparing to unpack .../084-libde265-0_1.0.11-1+deb12u2_amd64.deb ...
defender: Unpacking libde265-0:amd64 (1.0.11-1+deb12u2) ...
defender: Selecting previously unselected package libx265-199:amd64.
defender: Preparing to unpack .../085-libx265-199_3.5-2+b1_amd64.deb ...
defender: Unpacking libx265-199:amd64 (3.5-2+b1) ...
defender: Selecting previously unselected package libheif1:amd64.
defender: Preparing to unpack .../086-libheif1_1.15.1-1+deb12u1_amd64.deb ...
defender: Unpacking libheif1:amd64 (1.15.1-1+deb12u1) ...
defender: Selecting previously unselected package libdeflate0:amd64.
defender: Preparing to unpack .../087-libdeflate0_1.14-1_amd64.deb ...
defender: Unpacking libdeflate0:amd64 (1.14-1) ...
defender: Selecting previously unselected package libjbig0:amd64.
defender: Preparing to unpack .../088-libjbig0_2.1-6.1_amd64.deb ...
defender: Unpacking libjbig0:amd64 (2.1-6.1) ...
defender: Selecting previously unselected package liblerc4:amd64.
defender: Preparing to unpack .../089-liblerc4_4.0.0+ds-2_amd64.deb ...
defender: Unpacking liblerc4:amd64 (4.0.0+ds-2) ...
defender: Selecting previously unselected package libwebp7:amd64.
defender: Preparing to unpack .../090-libwebp7_1.2.4-0.2+deb12u1_amd64.deb ...
defender: Unpacking libwebp7:amd64 (1.2.4-0.2+deb12u1) ...
defender: Selecting previously unselected package libtiff6:amd64.
defender: Preparing to unpack .../091-libtiff6_4.5.0-6+deb12u4_amd64.deb ...
defender: Unpacking libtiff6:amd64 (4.5.0-6+deb12u4) ...
defender: Selecting previously unselected package libxau6:amd64.
defender: Preparing to unpack .../092-libxau6_1%3a1.0.9-1_amd64.deb ...
defender: Unpacking libxau6:amd64 (1:1.0.9-1) ...
defender: Selecting previously unselected package libxdmcp6:amd64.
defender: Preparing to unpack .../093-libxdmcp6_1%3a1.1.2-3_amd64.deb ...
defender: Unpacking libxdmcp6:amd64 (1:1.1.2-3) ...
defender: Selecting previously unselected package libxcb1:amd64.
defender: Preparing to unpack .../094-libxcb1_1.15-1_amd64.deb ...
defender: Unpacking libxcb1:amd64 (1.15-1) ...
defender: Selecting previously unselected package libx11-data.
defender: Preparing to unpack .../095-libx11-data_2%3a1.8.4-2+deb12u2_all.deb ...
defender: Unpacking libx11-data (2:1.8.4-2+deb12u2) ...
defender: Selecting previously unselected package libx11-6:amd64.
defender: Preparing to unpack .../096-libx11-6_2%3a1.8.4-2+deb12u2_amd64.deb ...
defender: Unpacking libx11-6:amd64 (2:1.8.4-2+deb12u2) ...
defender: Selecting previously unselected package libxpm4:amd64.
defender: Preparing to unpack .../097-libxpm4_1%3a3.5.12-1.1+deb12u1_amd64.deb ...
defender: Unpacking libxpm4:amd64 (1:3.5.12-1.1+deb12u1) ...
defender: Selecting previously unselected package libgd3:amd64.
defender: Preparing to unpack .../098-libgd3_2.3.3-9_amd64.deb ...
defender: Unpacking libgd3:amd64 (2.3.3-9) ...
defender: Selecting previously unselected package libc-devtools.
defender: Preparing to unpack .../099-libc-devtools_2.36-9+deb12u13_amd64.deb ...
defender: Unpacking libc-devtools (2.36-9+deb12u13) ...
defender: Selecting previously unselected package libevent-core-2.1-7:amd64.
defender: Preparing to unpack .../100-libevent-core-2.1-7_2.1.12-stable-8_amd64.deb ...
defender: Unpacking libevent-core-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Selecting previously unselected package libfile-fcntllock-perl.
defender: Preparing to unpack .../101-libfile-fcntllock-perl_0.22-4+b1_amd64.deb ...
defender: Unpacking libfile-fcntllock-perl (0.22-4+b1) ...
defender: Selecting previously unselected package libgpm2:amd64.
defender: Preparing to unpack .../102-libgpm2_1.20.7-10+b1_amd64.deb ...
defender: Unpacking libgpm2:amd64 (1.20.7-10+b1) ...
defender: Selecting previously unselected package libsodium23:amd64.
defender: Preparing to unpack .../103-libsodium23_1.0.18-1+deb12u1_amd64.deb ...
defender: Unpacking libsodium23:amd64 (1.0.18-1+deb12u1) ...
defender: Selecting previously unselected package libutempter0:amd64.
defender: Preparing to unpack .../104-libutempter0_1.2.1-3_amd64.deb ...
defender: Unpacking libutempter0:amd64 (1.2.1-3) ...
defender: Selecting previously unselected package manpages-dev.
defender: Preparing to unpack .../105-manpages-dev_6.03-2_all.deb ...
defender: Unpacking manpages-dev (6.03-2) ...
defender: Selecting previously unselected package tmux.
defender: Preparing to unpack .../106-tmux_3.3a-3_amd64.deb ...
defender: Unpacking tmux (3.3a-3) ...
defender: Selecting previously unselected package vim-runtime.
defender: Preparing to unpack .../107-vim-runtime_2%3a9.0.1378-2+deb12u2_all.deb ...
defender: Adding 'diversion of /usr/share/vim/vim90/doc/help.txt to /usr/share/vim/vim90/doc/help.txt.vim-tiny by vim-runtime'
defender: Adding 'diversion of /usr/share/vim/vim90/doc/tags to /usr/share/vim/vim90/doc/tags.vim-tiny by vim-runtime'
defender: Unpacking vim-runtime (2:9.0.1378-2+deb12u2) ...
defender: Selecting previously unselected package vim.
defender: Preparing to unpack .../108-vim_2%3a9.0.1378-2+deb12u2_amd64.deb ...
defender: Unpacking vim (2:9.0.1378-2+deb12u2) ...
defender: Selecting previously unselected package xxd.
defender: Preparing to unpack .../109-xxd_2%3a9.0.1378-2+deb12u2_amd64.deb ...
defender: Unpacking xxd (2:9.0.1378-2+deb12u2) ...
defender: Setting up libksba8:amd64 (1.6.3-2) ...
defender: Setting up libaom3:amd64 (3.6.0-1+deb12u2) ...
defender: Setting up manpages-dev (6.03-2) ...
defender: Setting up libabsl20220623:amd64 (20220623.1-1+deb12u2) ...
defender: Setting up libxau6:amd64 (1:1.0.9-1) ...
defender: Setting up libxdmcp6:amd64 (1:1.1.2-3) ...
defender: Setting up libc-l10n (2.36-9+deb12u13) ...
defender: Setting up libxcb1:amd64 (1.15-1) ...
defender: Setting up libsodium23:amd64 (1.0.18-1+deb12u1) ...
defender: Setting up libgpm2:amd64 (1.20.7-10+b1) ...
defender: Setting up liblerc4:amd64 (4.0.0+ds-2) ...
defender: Setting up wget (1.21.3-1+deb12u1) ...
defender: Setting up libfile-fcntllock-perl (0.22-4+b1) ...
defender: Setting up libalgorithm-diff-perl (1.201-1) ...
defender: Setting up binutils-common:amd64 (2.40-2) ...
defender: Setting up libdeflate0:amd64 (1.14-1) ...
defender: Setting up linux-libc-dev:amd64 (6.1.170-1) ...
defender: Setting up libctf-nobfd0:amd64 (2.40-2) ...
defender: Setting up libcurl3-gnutls:amd64 (7.88.1-10+deb12u14) ...
defender: Setting up libnpth0:amd64 (1.6-3) ...
defender: Setting up libsvtav1enc1:amd64 (1.4.1+dfsg-1) ...
defender: Setting up libassuan0:amd64 (2.5.5-5) ...
defender: Setting up libgomp1:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up locales (2.36-9+deb12u13) ...
defender: Generating locales (this might take a while)...
defender: Generation complete.
defender: Setting up libjbig0:amd64 (2.1-6.1) ...
defender: Setting up librav1e0:amd64 (0.5.1-6) ...
defender: Setting up xxd (2:9.0.1378-2+deb12u2) ...
defender: Setting up libfakeroot:amd64 (1.31-1.2) ...
defender: Setting up fakeroot (1.31-1.2) ...
defender: update-alternatives: using /usr/bin/fakeroot-sysv to provide /usr/bin/fakeroot (fakeroot) in auto mode
defender: Setting up liberror-perl (0.17029-2) ...
defender: Setting up libtirpc-dev:amd64 (1.3.3+ds-1) ...
defender: Setting up rpcsvc-proto (1.4.3-1) ...
defender: Setting up vim-common (2:9.0.1378-2+deb12u2) ...
defender: Setting up libjpeg62-turbo:amd64 (1:2.1.5-2) ...
defender: Setting up libx11-data (2:1.8.4-2+deb12u2) ...
defender: Setting up make (4.3-4.1) ...
defender: Setting up libmpfr6:amd64 (4.2.0-1) ...
defender: Setting up gnupg-l10n (2.2.40-1.1+deb12u2) ...
defender: Setting up libquadmath0:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libmpc3:amd64 (1.3.1-1) ...
defender: Setting up libevent-core-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Setting up libatomic1:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up patch (2.7.6-7) ...
defender: Setting up fonts-dejavu-core (2.37-6) ...
defender: Setting up libgav1-1:amd64 (0.18.0-1+b1) ...
defender: Setting up libdav1d6:amd64 (1.0.0-2+deb12u1) ...
defender: Setting up libdpkg-perl (1.21.22) ...
defender: Setting up libx265-199:amd64 (3.5-2+b1) ...
defender: Setting up libwebp7:amd64 (1.2.4-0.2+deb12u1) ...
defender: Setting up libutempter0:amd64 (1.2.1-3) ...
defender: Setting up libubsan1:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libnsl-dev:amd64 (1.3.0-2) ...
defender: Setting up libcrypt-dev:amd64 (1:4.4.33-2) ...
defender: Setting up libtiff6:amd64 (4.5.0-6+deb12u4) ...
defender: Setting up libasan8:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up gpgconf (2.2.40-1.1+deb12u2) ...
defender: Setting up libcurl4:amd64 (7.88.1-10+deb12u14) ...
defender: Setting up git-man (1:2.39.5-0+deb12u3) ...
defender: Setting up libx11-6:amd64 (2:1.8.4-2+deb12u2) ...
defender: Setting up curl (7.88.1-10+deb12u14) ...
defender: Setting up libtsan2:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libbinutils:amd64 (2.40-2) ...
defender: Setting up vim-runtime (2:9.0.1378-2+deb12u2) ...
defender: Setting up libisl23:amd64 (0.25-1.1) ...
defender: Setting up libde265-0:amd64 (1.0.11-1+deb12u2) ...
defender: Setting up libc-dev-bin (2.36-9+deb12u13) ...
defender: Setting up libyuv0:amd64 (0.0~git20230123.b2528b0-1) ...
defender: Setting up libalgorithm-diff-xs-perl:amd64 (0.04-8+b1) ...
defender: Setting up tmux (3.3a-3) ...
defender: Setting up libcc1-0:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libonig5:amd64 (6.9.8-1) ...
defender: Setting up gpg (2.2.40-1.1+deb12u2) ...
defender: Setting up liblsan0:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libitm1:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up rsync (3.2.7-1+deb12u4) ...
defender: rsync.service is a disabled or a static unit, not starting it.
defender: Setting up libalgorithm-merge-perl (0.08-5) ...
defender: Setting up gnupg-utils (2.2.40-1.1+deb12u2) ...
defender: Setting up libctf0:amd64 (2.40-2) ...
defender: Setting up pinentry-curses (1.2.1-1) ...
defender: Setting up cpp-12 (12.2.0-14+deb12u1) ...
defender: Setting up vim (2:9.0.1378-2+deb12u2) ...
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/ex (ex) in auto mode
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/rview (rview) in auto mode
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/rvim (rvim) in auto mode
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/vi (vi) in auto mode
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/view (view) in auto mode
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/vim (vim) in auto mode
defender: update-alternatives: using /usr/bin/vim.basic to provide /usr/bin/vimdiff (vimdiff) in auto mode
defender: Setting up gpg-agent (2.2.40-1.1+deb12u2) ...
defender: Created symlink /etc/systemd/user/sockets.target.wants/gpg-agent-browser.socket → /usr/lib/systemd/user/gpg-agent-browser.socket.
defender: Created symlink /etc/systemd/user/sockets.target.wants/gpg-agent-extra.socket → /usr/lib/systemd/user/gpg-agent-extra.socket.
defender: Created symlink /etc/systemd/user/sockets.target.wants/gpg-agent-ssh.socket → /usr/lib/systemd/user/gpg-agent-ssh.socket.
defender: Created symlink /etc/systemd/user/sockets.target.wants/gpg-agent.socket → /usr/lib/systemd/user/gpg-agent.socket.
defender: Setting up libxpm4:amd64 (1:3.5.12-1.1+deb12u1) ...
defender: Setting up libavif15:amd64 (0.11.1-1+deb12u1) ...
defender: Setting up libjq1:amd64 (1.6-2.1+deb12u1) ...
defender: Setting up fontconfig-config (2.14.1-4) ...
defender: Setting up gpgsm (2.2.40-1.1+deb12u2) ...
defender: Setting up libheif1:amd64 (1.15.1-1+deb12u1) ...
defender: Setting up vim-tiny (2:9.0.1378-2+deb12u2) ...
defender: Setting up dirmngr (2.2.40-1.1+deb12u2) ...
defender: Created symlink /etc/systemd/user/sockets.target.wants/dirmngr.socket → /usr/lib/systemd/user/dirmngr.socket.
defender: Setting up libgprofng0:amd64 (2.40-2) ...
defender: Setting up libgcc-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up git (1:2.39.5-0+deb12u3) ...
defender: Setting up gpg-wks-server (2.2.40-1.1+deb12u2) ...
defender: Setting up cpp (4:12.2.0-3) ...
defender: Setting up jq (1.6-2.1+deb12u1) ...
defender: Setting up libc6-dev:amd64 (2.36-9+deb12u13) ...
defender: Setting up libfontconfig1:amd64 (2.14.1-4) ...
defender: Setting up binutils-x86-64-linux-gnu (2.40-2) ...
defender: Setting up gpg-wks-client (2.2.40-1.1+deb12u2) ...
defender: Setting up libstdc++-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up binutils (2.40-2) ...
defender: Setting up dpkg-dev (1.21.22) ...
defender: Setting up gcc-12 (12.2.0-14+deb12u1) ...
defender: Setting up libgd3:amd64 (2.3.3-9) ...
defender: Setting up gnupg (2.2.40-1.1+deb12u2) ...
defender: Setting up libc-devtools (2.36-9+deb12u13) ...
defender: Setting up g++-12 (12.2.0-14+deb12u1) ...
defender: Setting up gcc (4:12.2.0-3) ...
defender: Setting up g++ (4:12.2.0-3) ...
defender: update-alternatives: using /usr/bin/g++ to provide /usr/bin/c++ (c++) in auto mode
defender: Setting up build-essential (12.9) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for mailcap (3.70+nmu1) ...
defender: ++ apt-get install -y clang llvm bpftool linux-headers-amd64 libpcap-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   clang-14 firmware-linux-free icu-devtools lib32gcc-s1 lib32stdc++6
defender:   libc6-i386 libclang-common-14-dev libclang-cpp14 libclang-rt-14-dev
defender:   libclang1-14 libcurl3-nss libdbus-1-dev libffi-dev libgc1 libicu-dev
defender:   libicu72 libllvm14 libncurses-dev libncurses6 libnspr4 libnss3
defender:   libobjc-12-dev libobjc4 libpcap0.8-dev libpfm4 libpkgconf3 libtinfo-dev
defender:   libxml2 libxml2-dev libyaml-0-2 libz3-4 libz3-dev linux-compiler-gcc-12-x86
defender:   linux-headers-6.1.0-45-amd64 linux-headers-6.1.0-45-common
defender:   linux-image-6.1.0-45-amd64 linux-image-amd64 linux-kbuild-6.1 llvm-14
defender:   llvm-14-dev llvm-14-linker-tools llvm-14-runtime llvm-14-tools llvm-runtime
defender:   nss-plugin-pem pkg-config pkgconf pkgconf-bin python3-pygments python3-yaml
defender:   sgml-base xml-core
defender: Suggested packages:
defender:   clang-14-doc wasi-libc icu-doc ncurses-doc linux-doc-6.1
defender:   debian-kernel-handbook llvm-14-doc python-pygments-doc ttf-bitstream-vera
defender:   sgml-base-doc debhelper
defender: The following NEW packages will be installed:
defender:   bpftool clang clang-14 firmware-linux-free icu-devtools lib32gcc-s1
defender:   lib32stdc++6 libc6-i386 libclang-common-14-dev libclang-cpp14
defender:   libclang-rt-14-dev libclang1-14 libcurl3-nss libdbus-1-dev libffi-dev libgc1
defender:   libicu-dev libllvm14 libncurses-dev libncurses6 libnspr4 libnss3
defender:   libobjc-12-dev libobjc4 libpcap-dev libpcap0.8-dev libpfm4 libpkgconf3
defender:   libtinfo-dev libxml2-dev libyaml-0-2 libz3-4 libz3-dev
defender:   linux-compiler-gcc-12-x86 linux-headers-6.1.0-45-amd64
defender:   linux-headers-6.1.0-45-common linux-headers-amd64 linux-image-6.1.0-45-amd64
defender:   linux-kbuild-6.1 llvm llvm-14 llvm-14-dev llvm-14-linker-tools
defender:   llvm-14-runtime llvm-14-tools llvm-runtime nss-plugin-pem pkg-config pkgconf
defender:   pkgconf-bin python3-pygments python3-yaml sgml-base xml-core
defender: The following packages will be upgraded:
defender:   libicu72 libxml2 linux-image-amd64
defender: 3 upgraded, 54 newly installed, 0 to remove and 83 not upgraded.
defender: Need to get 214 MB of archives.
defender: After this operation, 1190 MB of additional disk space will be used.
defender: Get:1 https://security.debian.org/debian-security bookworm-security/main amd64 bpftool amd64 7.1.0+6.1.170-1 [1376 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 sgml-base all 1.31 [15.4 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libicu72 amd64 72.1-3+deb12u1 [9376 kB]
defender: Get:4 https://security.debian.org/debian-security bookworm-security/main amd64 libnss3 amd64 2:3.87.1-1+deb12u2 [1332 kB]
defender: Get:5 https://security.debian.org/debian-security bookworm-security/main amd64 linux-compiler-gcc-12-x86 amd64 6.1.170-1 [1124 kB]
defender: Get:6 https://security.debian.org/debian-security bookworm-security/main amd64 linux-headers-6.1.0-45-common all 6.1.170-1 [10.3 MB]
defender: Get:7 https://security.debian.org/debian-security bookworm-security/main amd64 linux-kbuild-6.1 amd64 6.1.170-1 [1382 kB]
defender: Get:8 https://security.debian.org/debian-security bookworm-security/main amd64 linux-headers-6.1.0-45-amd64 amd64 6.1.170-1 [1655 kB]
defender: Get:9 https://security.debian.org/debian-security bookworm-security/main amd64 linux-headers-amd64 amd64 6.1.170-1 [1420 B]
defender: Get:10 https://security.debian.org/debian-security bookworm-security/main amd64 linux-image-6.1.0-45-amd64 amd64 6.1.170-1 [70.2 MB]
defender: Get:11 https://deb.debian.org/debian bookworm/main amd64 libxml2 amd64 2.9.14+dfsg-1.3~deb12u5 [688 kB]
defender: Get:12 https://deb.debian.org/debian bookworm/main amd64 libz3-4 amd64 4.8.12-3.1 [7216 kB]
defender: Get:13 https://deb.debian.org/debian bookworm/main amd64 libllvm14 amd64 1:14.0.6-12 [21.8 MB]
defender: Get:14 https://deb.debian.org/debian bookworm/main amd64 libclang-cpp14 amd64 1:14.0.6-12 [11.1 MB]
defender: Get:15 https://deb.debian.org/debian bookworm/main amd64 libgc1 amd64 1:8.2.2-3 [245 kB]
defender: Get:16 https://deb.debian.org/debian bookworm/main amd64 libobjc4 amd64 12.2.0-14+deb12u1 [43.2 kB]
defender: Get:17 https://deb.debian.org/debian bookworm/main amd64 libobjc-12-dev amd64 12.2.0-14+deb12u1 [170 kB]
defender: Get:18 https://deb.debian.org/debian bookworm/main amd64 libclang-common-14-dev all 1:14.0.6-12 [890 kB]
defender: Get:19 https://deb.debian.org/debian bookworm/main amd64 llvm-14-linker-tools amd64 1:14.0.6-12 [1288 kB]
defender: Get:20 https://deb.debian.org/debian bookworm/main amd64 libclang1-14 amd64 1:14.0.6-12 [6157 kB]
defender: Get:21 https://deb.debian.org/debian bookworm/main amd64 clang-14 amd64 1:14.0.6-12 [102 kB]
defender: Get:22 https://deb.debian.org/debian bookworm/main amd64 clang amd64 1:14.0-55.7~deb12u1 [5144 B]
defender: Get:23 https://deb.debian.org/debian bookworm/main amd64 firmware-linux-free all 20200122-1 [24.2 kB]
defender: Get:24 https://deb.debian.org/debian bookworm/main amd64 icu-devtools amd64 72.1-3+deb12u1 [206 kB]
defender: Get:25 https://deb.debian.org/debian bookworm/main amd64 libc6-i386 amd64 2.36-9+deb12u13 [2459 kB]
defender: Get:26 https://deb.debian.org/debian bookworm/main amd64 lib32gcc-s1 amd64 12.2.0-14+deb12u1 [59.7 kB]
defender: Get:27 https://deb.debian.org/debian bookworm/main amd64 lib32stdc++6 amd64 12.2.0-14+deb12u1 [643 kB]
defender: Get:28 https://deb.debian.org/debian bookworm/main amd64 libclang-rt-14-dev amd64 1:14.0.6-12 [3275 kB]
defender: Get:29 https://deb.debian.org/debian bookworm/main amd64 libnspr4 amd64 2:4.35-1 [113 kB]
defender: Get:30 https://deb.debian.org/debian bookworm/main amd64 nss-plugin-pem amd64 1.0.8+1-1 [54.6 kB]
defender: Get:31 https://deb.debian.org/debian bookworm/main amd64 libcurl3-nss amd64 7.88.1-10+deb12u14 [395 kB]
defender: Get:32 https://deb.debian.org/debian bookworm/main amd64 libpkgconf3 amd64 1.8.1-1 [36.1 kB]
defender: Get:33 https://deb.debian.org/debian bookworm/main amd64 pkgconf-bin amd64 1.8.1-1 [29.5 kB]
defender: Get:34 https://deb.debian.org/debian bookworm/main amd64 pkgconf amd64 1.8.1-1 [25.9 kB]
defender: Get:35 https://deb.debian.org/debian bookworm/main amd64 pkg-config amd64 1.8.1-1 [13.7 kB]
defender: Get:36 https://deb.debian.org/debian bookworm/main amd64 xml-core all 0.18+nmu1 [23.8 kB]
defender: Get:37 https://deb.debian.org/debian bookworm/main amd64 libdbus-1-dev amd64 1.14.10-1~deb12u1 [241 kB]
defender: Get:38 https://security.debian.org/debian-security bookworm-security/main amd64 linux-image-amd64 amd64 6.1.170-1 [1480 B]
defender: Get:39 https://deb.debian.org/debian bookworm/main amd64 libffi-dev amd64 3.4.4-1 [59.4 kB]
defender: Get:40 https://deb.debian.org/debian bookworm/main amd64 libicu-dev amd64 72.1-3+deb12u1 [10.3 MB]
defender: Get:41 https://deb.debian.org/debian bookworm/main amd64 libncurses6 amd64 6.4-4 [103 kB]
defender: Get:42 https://deb.debian.org/debian bookworm/main amd64 libncurses-dev amd64 6.4-4 [349 kB]
defender: Get:43 https://deb.debian.org/debian bookworm/main amd64 libpcap0.8-dev amd64 1.10.3-1 [281 kB]
defender: Get:44 https://deb.debian.org/debian bookworm/main amd64 libpcap-dev amd64 1.10.3-1 [28.2 kB]
defender: Get:45 https://deb.debian.org/debian bookworm/main amd64 libpfm4 amd64 4.13.0-1 [294 kB]
defender: Get:46 https://deb.debian.org/debian bookworm/main amd64 libtinfo-dev amd64 6.4-4 [924 B]
defender: Get:47 https://deb.debian.org/debian bookworm/main amd64 libxml2-dev amd64 2.9.14+dfsg-1.3~deb12u5 [784 kB]
defender: Get:48 https://deb.debian.org/debian bookworm/main amd64 libyaml-0-2 amd64 0.2.5-1 [53.6 kB]
defender: Get:49 https://deb.debian.org/debian bookworm/main amd64 libz3-dev amd64 4.8.12-3.1 [90.6 kB]
defender: Get:50 https://deb.debian.org/debian bookworm/main amd64 llvm-14-runtime amd64 1:14.0.6-12 [477 kB]
defender: Get:51 https://deb.debian.org/debian bookworm/main amd64 llvm-runtime amd64 1:14.0-55.7~deb12u1 [4812 B]
defender: Get:52 https://deb.debian.org/debian bookworm/main amd64 llvm-14 amd64 1:14.0.6-12 [11.7 MB]
defender: Get:53 https://deb.debian.org/debian bookworm/main amd64 llvm amd64 1:14.0-55.7~deb12u1 [7212 B]
defender: Get:54 https://deb.debian.org/debian bookworm/main amd64 python3-pygments all 2.14.0+dfsg-1 [783 kB]
defender: Get:55 https://deb.debian.org/debian bookworm/main amd64 python3-yaml amd64 6.0-3+b2 [119 kB]
defender: Get:56 https://deb.debian.org/debian bookworm/main amd64 llvm-14-tools amd64 1:14.0.6-12 [405 kB]
defender: Get:57 https://deb.debian.org/debian bookworm/main amd64 llvm-14-dev amd64 1:14.0.6-12 [33.9 MB]
defender: apt-listchanges: Reading changelogs...
defender: Fetched 214 MB in 1min 22s (2618 kB/s)
defender: Selecting previously unselected package sgml-base.
(Reading database ... 35892 files and directories currently installed.)
defender: Preparing to unpack .../00-sgml-base_1.31_all.deb ...
defender: Unpacking sgml-base (1.31) ...
defender: Selecting previously unselected package bpftool.
defender: Preparing to unpack .../01-bpftool_7.1.0+6.1.170-1_amd64.deb ...
defender: Unpacking bpftool (7.1.0+6.1.170-1) ...
defender: Preparing to unpack .../02-libicu72_72.1-3+deb12u1_amd64.deb ...
defender: Unpacking libicu72:amd64 (72.1-3+deb12u1) over (72.1-3) ...
defender: Preparing to unpack .../03-libxml2_2.9.14+dfsg-1.3~deb12u5_amd64.deb ...
defender: Unpacking libxml2:amd64 (2.9.14+dfsg-1.3~deb12u5) over (2.9.14+dfsg-1.3~deb12u1) ...
defender: Selecting previously unselected package libz3-4:amd64.
defender: Preparing to unpack .../04-libz3-4_4.8.12-3.1_amd64.deb ...
defender: Unpacking libz3-4:amd64 (4.8.12-3.1) ...
defender: Selecting previously unselected package libllvm14:amd64.
defender: Preparing to unpack .../05-libllvm14_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking libllvm14:amd64 (1:14.0.6-12) ...
defender: Selecting previously unselected package libclang-cpp14.
defender: Preparing to unpack .../06-libclang-cpp14_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking libclang-cpp14 (1:14.0.6-12) ...
defender: Selecting previously unselected package libgc1:amd64.
defender: Preparing to unpack .../07-libgc1_1%3a8.2.2-3_amd64.deb ...
defender: Unpacking libgc1:amd64 (1:8.2.2-3) ...
defender: Selecting previously unselected package libobjc4:amd64.
defender: Preparing to unpack .../08-libobjc4_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libobjc4:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libobjc-12-dev:amd64.
defender: Preparing to unpack .../09-libobjc-12-dev_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libobjc-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libclang-common-14-dev.
defender: Preparing to unpack .../10-libclang-common-14-dev_1%3a14.0.6-12_all.deb ...
defender: Unpacking libclang-common-14-dev (1:14.0.6-12) ...
defender: Selecting previously unselected package llvm-14-linker-tools.
defender: Preparing to unpack .../11-llvm-14-linker-tools_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking llvm-14-linker-tools (1:14.0.6-12) ...
defender: Selecting previously unselected package libclang1-14.
defender: Preparing to unpack .../12-libclang1-14_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking libclang1-14 (1:14.0.6-12) ...
defender: Selecting previously unselected package clang-14.
defender: Preparing to unpack .../13-clang-14_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking clang-14 (1:14.0.6-12) ...
defender: Selecting previously unselected package clang.
defender: Preparing to unpack .../14-clang_1%3a14.0-55.7~deb12u1_amd64.deb ...
defender: Unpacking clang (1:14.0-55.7~deb12u1) ...
defender: Selecting previously unselected package firmware-linux-free.
defender: Preparing to unpack .../15-firmware-linux-free_20200122-1_all.deb ...
defender: Unpacking firmware-linux-free (20200122-1) ...
defender: Selecting previously unselected package icu-devtools.
defender: Preparing to unpack .../16-icu-devtools_72.1-3+deb12u1_amd64.deb ...
defender: Unpacking icu-devtools (72.1-3+deb12u1) ...
defender: Selecting previously unselected package libc6-i386.
defender: Preparing to unpack .../17-libc6-i386_2.36-9+deb12u13_amd64.deb ...
defender: Unpacking libc6-i386 (2.36-9+deb12u13) ...
defender: Selecting previously unselected package lib32gcc-s1.
defender: Preparing to unpack .../18-lib32gcc-s1_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking lib32gcc-s1 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package lib32stdc++6.
defender: Preparing to unpack .../19-lib32stdc++6_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking lib32stdc++6 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libclang-rt-14-dev:amd64.
defender: Preparing to unpack .../20-libclang-rt-14-dev_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking libclang-rt-14-dev:amd64 (1:14.0.6-12) ...
defender: Selecting previously unselected package libnspr4:amd64.
defender: Preparing to unpack .../21-libnspr4_2%3a4.35-1_amd64.deb ...
defender: Unpacking libnspr4:amd64 (2:4.35-1) ...
defender: Selecting previously unselected package libnss3:amd64.
defender: Preparing to unpack .../22-libnss3_2%3a3.87.1-1+deb12u2_amd64.deb ...
defender: Unpacking libnss3:amd64 (2:3.87.1-1+deb12u2) ...
defender: Selecting previously unselected package nss-plugin-pem:amd64.
defender: Preparing to unpack .../23-nss-plugin-pem_1.0.8+1-1_amd64.deb ...
defender: Unpacking nss-plugin-pem:amd64 (1.0.8+1-1) ...
defender: Selecting previously unselected package libcurl3-nss:amd64.
defender: Preparing to unpack .../24-libcurl3-nss_7.88.1-10+deb12u14_amd64.deb ...
defender: Unpacking libcurl3-nss:amd64 (7.88.1-10+deb12u14) ...
defender: Selecting previously unselected package libpkgconf3:amd64.
defender: Preparing to unpack .../25-libpkgconf3_1.8.1-1_amd64.deb ...
defender: Unpacking libpkgconf3:amd64 (1.8.1-1) ...
defender: Selecting previously unselected package pkgconf-bin.
defender: Preparing to unpack .../26-pkgconf-bin_1.8.1-1_amd64.deb ...
defender: Unpacking pkgconf-bin (1.8.1-1) ...
defender: Selecting previously unselected package pkgconf:amd64.
defender: Preparing to unpack .../27-pkgconf_1.8.1-1_amd64.deb ...
defender: Unpacking pkgconf:amd64 (1.8.1-1) ...
defender: Selecting previously unselected package pkg-config:amd64.
defender: Preparing to unpack .../28-pkg-config_1.8.1-1_amd64.deb ...
defender: Unpacking pkg-config:amd64 (1.8.1-1) ...
defender: Selecting previously unselected package xml-core.
defender: Preparing to unpack .../29-xml-core_0.18+nmu1_all.deb ...
defender: Unpacking xml-core (0.18+nmu1) ...
defender: Selecting previously unselected package libdbus-1-dev:amd64.
defender: Preparing to unpack .../30-libdbus-1-dev_1.14.10-1~deb12u1_amd64.deb ...
defender: Unpacking libdbus-1-dev:amd64 (1.14.10-1~deb12u1) ...
defender: Selecting previously unselected package libffi-dev:amd64.
defender: Preparing to unpack .../31-libffi-dev_3.4.4-1_amd64.deb ...
defender: Unpacking libffi-dev:amd64 (3.4.4-1) ...
defender: Selecting previously unselected package libicu-dev:amd64.
defender: Preparing to unpack .../32-libicu-dev_72.1-3+deb12u1_amd64.deb ...
defender: Unpacking libicu-dev:amd64 (72.1-3+deb12u1) ...
defender: Selecting previously unselected package libncurses6:amd64.
defender: Preparing to unpack .../33-libncurses6_6.4-4_amd64.deb ...
defender: Unpacking libncurses6:amd64 (6.4-4) ...
defender: Selecting previously unselected package libncurses-dev:amd64.
defender: Preparing to unpack .../34-libncurses-dev_6.4-4_amd64.deb ...
defender: Unpacking libncurses-dev:amd64 (6.4-4) ...
defender: Selecting previously unselected package libpcap0.8-dev:amd64.
defender: Preparing to unpack .../35-libpcap0.8-dev_1.10.3-1_amd64.deb ...
defender: Unpacking libpcap0.8-dev:amd64 (1.10.3-1) ...
defender: Selecting previously unselected package libpcap-dev:amd64.
defender: Preparing to unpack .../36-libpcap-dev_1.10.3-1_amd64.deb ...
defender: Unpacking libpcap-dev:amd64 (1.10.3-1) ...
defender: Selecting previously unselected package libpfm4:amd64.
defender: Preparing to unpack .../37-libpfm4_4.13.0-1_amd64.deb ...
defender: Unpacking libpfm4:amd64 (4.13.0-1) ...
defender: Selecting previously unselected package libtinfo-dev:amd64.
defender: Preparing to unpack .../38-libtinfo-dev_6.4-4_amd64.deb ...
defender: Unpacking libtinfo-dev:amd64 (6.4-4) ...
defender: Selecting previously unselected package libxml2-dev:amd64.
defender: Preparing to unpack .../39-libxml2-dev_2.9.14+dfsg-1.3~deb12u5_amd64.deb ...
defender: Unpacking libxml2-dev:amd64 (2.9.14+dfsg-1.3~deb12u5) ...
defender: Selecting previously unselected package libyaml-0-2:amd64.
defender: Preparing to unpack .../40-libyaml-0-2_0.2.5-1_amd64.deb ...
defender: Unpacking libyaml-0-2:amd64 (0.2.5-1) ...
defender: Selecting previously unselected package libz3-dev:amd64.
defender: Preparing to unpack .../41-libz3-dev_4.8.12-3.1_amd64.deb ...
defender: Unpacking libz3-dev:amd64 (4.8.12-3.1) ...
defender: Selecting previously unselected package linux-compiler-gcc-12-x86.
defender: Preparing to unpack .../42-linux-compiler-gcc-12-x86_6.1.170-1_amd64.deb ...
defender: Unpacking linux-compiler-gcc-12-x86 (6.1.170-1) ...
defender: Selecting previously unselected package linux-headers-6.1.0-45-common.
defender: Preparing to unpack .../43-linux-headers-6.1.0-45-common_6.1.170-1_all.deb ...
defender: Unpacking linux-headers-6.1.0-45-common (6.1.170-1) ...
defender: Selecting previously unselected package linux-kbuild-6.1.
defender: Preparing to unpack .../44-linux-kbuild-6.1_6.1.170-1_amd64.deb ...
defender: Unpacking linux-kbuild-6.1 (6.1.170-1) ...
defender: Selecting previously unselected package linux-headers-6.1.0-45-amd64.
defender: Preparing to unpack .../45-linux-headers-6.1.0-45-amd64_6.1.170-1_amd64.deb ...
defender: Unpacking linux-headers-6.1.0-45-amd64 (6.1.170-1) ...
defender: Selecting previously unselected package linux-headers-amd64.
defender: Preparing to unpack .../46-linux-headers-amd64_6.1.170-1_amd64.deb ...
defender: Unpacking linux-headers-amd64 (6.1.170-1) ...
defender: Selecting previously unselected package linux-image-6.1.0-45-amd64.
defender: Preparing to unpack .../47-linux-image-6.1.0-45-amd64_6.1.170-1_amd64.deb ...
defender: Unpacking linux-image-6.1.0-45-amd64 (6.1.170-1) ...
defender: Preparing to unpack .../48-linux-image-amd64_6.1.170-1_amd64.deb ...
defender: Unpacking linux-image-amd64 (6.1.170-1) over (6.1.106-3) ...
defender: Selecting previously unselected package llvm-14-runtime.
defender: Preparing to unpack .../49-llvm-14-runtime_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking llvm-14-runtime (1:14.0.6-12) ...
defender: Selecting previously unselected package llvm-runtime:amd64.
defender: Preparing to unpack .../50-llvm-runtime_1%3a14.0-55.7~deb12u1_amd64.deb ...
defender: Unpacking llvm-runtime:amd64 (1:14.0-55.7~deb12u1) ...
defender: Selecting previously unselected package llvm-14.
defender: Preparing to unpack .../51-llvm-14_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking llvm-14 (1:14.0.6-12) ...
defender: Selecting previously unselected package llvm.
defender: Preparing to unpack .../52-llvm_1%3a14.0-55.7~deb12u1_amd64.deb ...
defender: Unpacking llvm (1:14.0-55.7~deb12u1) ...
defender: Selecting previously unselected package python3-pygments.
defender: Preparing to unpack .../53-python3-pygments_2.14.0+dfsg-1_all.deb ...
defender: Unpacking python3-pygments (2.14.0+dfsg-1) ...
defender: Selecting previously unselected package python3-yaml.
defender: Preparing to unpack .../54-python3-yaml_6.0-3+b2_amd64.deb ...
defender: Unpacking python3-yaml (6.0-3+b2) ...
defender: Selecting previously unselected package llvm-14-tools.
defender: Preparing to unpack .../55-llvm-14-tools_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking llvm-14-tools (1:14.0.6-12) ...
defender: Selecting previously unselected package llvm-14-dev.
defender: Preparing to unpack .../56-llvm-14-dev_1%3a14.0.6-12_amd64.deb ...
defender: Unpacking llvm-14-dev (1:14.0.6-12) ...
defender: Setting up linux-headers-6.1.0-45-common (6.1.170-1) ...
defender: Setting up libicu72:amd64 (72.1-3+deb12u1) ...
defender: Setting up firmware-linux-free (20200122-1) ...
defender: Setting up libyaml-0-2:amd64 (0.2.5-1) ...
defender: Setting up bpftool (7.1.0+6.1.170-1) ...
defender: Setting up python3-yaml (6.0-3+b2) ...
defender: Setting up libffi-dev:amd64 (3.4.4-1) ...
defender: Setting up linux-compiler-gcc-12-x86 (6.1.170-1) ...
defender: Setting up python3-pygments (2.14.0+dfsg-1) ...
defender: Setting up libz3-4:amd64 (4.8.12-3.1) ...
defender: Setting up libpkgconf3:amd64 (1.8.1-1) ...
defender: Setting up libpfm4:amd64 (4.13.0-1) ...
defender: Setting up libnspr4:amd64 (2:4.35-1) ...
defender: Setting up libncurses6:amd64 (6.4-4) ...
defender: Setting up icu-devtools (72.1-3+deb12u1) ...
defender: Setting up pkgconf-bin (1.8.1-1) ...
defender: Setting up libgc1:amd64 (1:8.2.2-3) ...
defender: Setting up libc6-i386 (2.36-9+deb12u13) ...
defender: Setting up sgml-base (1.31) ...
defender: Setting up linux-kbuild-6.1 (6.1.170-1) ...
defender: Setting up libicu-dev:amd64 (72.1-3+deb12u1) ...
defender: Setting up libxml2:amd64 (2.9.14+dfsg-1.3~deb12u5) ...
defender: Setting up linux-image-6.1.0-45-amd64 (6.1.170-1) ...
defender: /etc/kernel/postinst.d/initramfs-tools:
defender: update-initramfs: Generating /boot/initrd.img-6.1.0-45-amd64
defender: W: No zstd in /usr/bin:/sbin:/bin, using gzip
defender: /etc/kernel/postinst.d/zz-update-grub:
defender: Generating grub configuration file ...
defender: Found linux image: /boot/vmlinuz-6.1.0-45-amd64
defender: Found initrd image: /boot/initrd.img-6.1.0-45-amd64
defender: Found linux image: /boot/vmlinuz-6.1.0-25-amd64
defender: Found initrd image: /boot/initrd.img-6.1.0-25-amd64
defender: done
defender: Setting up linux-headers-6.1.0-45-amd64 (6.1.170-1) ...
defender: Setting up libz3-dev:amd64 (4.8.12-3.1) ...
defender: Setting up libncurses-dev:amd64 (6.4-4) ...
defender: Setting up linux-headers-amd64 (6.1.170-1) ...
defender: Setting up libobjc4:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libnss3:amd64 (2:3.87.1-1+deb12u2) ...
defender: Setting up linux-image-amd64 (6.1.170-1) ...
defender: Setting up pkgconf:amd64 (1.8.1-1) ...
defender: Setting up libxml2-dev:amd64 (2.9.14+dfsg-1.3~deb12u5) ...
defender: Setting up lib32gcc-s1 (12.2.0-14+deb12u1) ...
defender: Setting up lib32stdc++6 (12.2.0-14+deb12u1) ...
defender: Setting up pkg-config:amd64 (1.8.1-1) ...
defender: Setting up libllvm14:amd64 (1:14.0.6-12) ...
defender: Setting up libobjc-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up xml-core (0.18+nmu1) ...
defender: Setting up llvm-14-linker-tools (1:14.0.6-12) ...
defender: Setting up llvm-14-tools (1:14.0.6-12) ...
defender: Setting up libtinfo-dev:amd64 (6.4-4) ...
defender: Setting up nss-plugin-pem:amd64 (1.0.8+1-1) ...
defender: Setting up libclang1-14 (1:14.0.6-12) ...
defender: Setting up llvm-14-runtime (1:14.0.6-12) ...
defender: Setting up libclang-rt-14-dev:amd64 (1:14.0.6-12) ...
defender: Setting up llvm-runtime:amd64 (1:14.0-55.7~deb12u1) ...
defender: Setting up libclang-common-14-dev (1:14.0.6-12) ...
defender: Setting up libclang-cpp14 (1:14.0.6-12) ...
defender: Setting up libcurl3-nss:amd64 (7.88.1-10+deb12u14) ...
defender: Setting up llvm-14 (1:14.0.6-12) ...
defender: Setting up clang-14 (1:14.0.6-12) ...
defender: Setting up clang (1:14.0-55.7~deb12u1) ...
defender: Setting up llvm (1:14.0-55.7~deb12u1) ...
defender: Setting up llvm-14-dev (1:14.0.6-12) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: Processing triggers for systemd (252.30-1~deb12u2) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for sgml-base (1.31) ...
defender: Setting up libdbus-1-dev:amd64 (1.14.10-1~deb12u1) ...
defender: Setting up libpcap0.8-dev:amd64 (1.10.3-1) ...
defender: Setting up libpcap-dev:amd64 (1.10.3-1) ...
defender: Processing triggers for initramfs-tools (0.142+deb12u1) ...
defender: update-initramfs: Generating /boot/initrd.img-6.1.0-45-amd64
defender: W: No zstd in /usr/bin:/sbin:/bin, using gzip
defender: +++ PKG_CONFIG_PATH=/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:
defender: +++ pkg-config --modversion libbpf
defender: +++ echo 0.0.0
defender: ++ CURRENT_LIBBPF_VERSION=0.0.0
defender: +++ printf '%s
defender: ' 1.2.0 0.0.0
defender: +++ sort -V
defender: +++ head -n1
defender: ++ '[' 0.0.0 '!=' 1.2.0 ']'
defender: ++ echo '🔧 Upgrading libbpf to 1.4.6...'
defender: 🔧 Upgrading libbpf to 1.4.6...
defender: ++ apt-get install -y libelf-dev zlib1g-dev pkg-config
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: pkg-config is already the newest version (1.8.1-1).
defender: pkg-config set to manually installed.
defender: The following NEW packages will be installed:
defender:   libelf-dev zlib1g-dev
defender: 0 upgraded, 2 newly installed, 0 to remove and 83 not upgraded.
defender: Need to get 989 kB of archives.
defender: After this operation, 1700 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 zlib1g-dev amd64 1:1.2.13.dfsg-1 [916 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libelf-dev amd64 0.188-2.1 [72.9 kB]
defender: Fetched 989 kB in 0s (2500 kB/s)
defender: Selecting previously unselected package zlib1g-dev:amd64.
(Reading database ... 62197 files and directories currently installed.)
defender: Preparing to unpack .../zlib1g-dev_1%3a1.2.13.dfsg-1_amd64.deb ...
defender: Unpacking zlib1g-dev:amd64 (1:1.2.13.dfsg-1) ...
defender: Selecting previously unselected package libelf-dev:amd64.
defender: Preparing to unpack .../libelf-dev_0.188-2.1_amd64.deb ...
defender: Unpacking libelf-dev:amd64 (0.188-2.1) ...
defender: Setting up zlib1g-dev:amd64 (1:1.2.13.dfsg-1) ...
defender: Setting up libelf-dev:amd64 (0.188-2.1) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: ++ cd /tmp
defender: ++ rm -rf libbpf
defender: ++ git clone --depth 1 --branch v1.4.6 https://github.com/libbpf/libbpf.git
defender: Cloning into 'libbpf'...
defender: Note: switching to 'fdf402b384cc42ce29bb9e27011633be3cbafe1e'.
defender:
defender: You are in 'detached HEAD' state. You can look around, make experimental
defender: changes and commit them, and you can discard any commits you make in this
defender: state without impacting any branches by switching back to a branch.
defender:
defender: If you want to create a new branch to retain commits you create, you may
defender: do so (now or later) by using -c with the switch command. Example:
defender:
defender:   git switch -c <new-branch-name>
defender:
defender: Or undo this operation with:
defender:
defender:   git switch -
defender:
defender: Turn off this advice by setting config variable advice.detachedHead to false
defender:
defender: ++ cd libbpf/src
defender: +++ nproc
defender: ++ make -j6 BUILD_STATIC_ONLY=y
defender:   MKDIR    staticobjs
defender:   CC       staticobjs/bpf.o
defender:   CC       staticobjs/btf.o
defender:   CC       staticobjs/libbpf.o
defender:   CC       staticobjs/libbpf_errno.o
defender:   CC       staticobjs/netlink.o
defender:   CC       staticobjs/nlattr.o
defender:   CC       staticobjs/str_error.o
defender:   CC       staticobjs/libbpf_probes.o
defender:   CC       staticobjs/bpf_prog_linfo.o
defender:   CC       staticobjs/btf_dump.o
defender:   CC       staticobjs/hashmap.o
defender:   CC       staticobjs/ringbuf.o
defender:   CC       staticobjs/strset.o
defender:   CC       staticobjs/linker.o
defender:   CC       staticobjs/gen_loader.o
defender:   CC       staticobjs/relo_core.o
defender:   CC       staticobjs/usdt.o
defender:   CC       staticobjs/zip.o
defender:   CC       staticobjs/elf.o
defender:   CC       staticobjs/features.o
defender:   AR       libbpf.a
defender: ++ make install install_headers
defender:   MKDIR    sharedobjs
defender:   CC       sharedobjs/bpf.o
defender:   CC       sharedobjs/btf.o
defender:   CC       sharedobjs/libbpf.o
defender:   CC       sharedobjs/libbpf_errno.o
defender:   CC       sharedobjs/netlink.o
defender:   CC       sharedobjs/nlattr.o
defender:   CC       sharedobjs/str_error.o
defender:   CC       sharedobjs/libbpf_probes.o
defender:   CC       sharedobjs/bpf_prog_linfo.o
defender:   CC       sharedobjs/btf_dump.o
defender:   CC       sharedobjs/hashmap.o
defender:   CC       sharedobjs/ringbuf.o
defender:   CC       sharedobjs/strset.o
defender:   CC       sharedobjs/linker.o
defender:   CC       sharedobjs/gen_loader.o
defender:   CC       sharedobjs/relo_core.o
defender:   CC       sharedobjs/usdt.o
defender:   CC       sharedobjs/zip.o
defender:   CC       sharedobjs/elf.o
defender:   CC       sharedobjs/features.o
defender:   CC       libbpf.so.1.4.6
defender:   INSTALL  bpf.h libbpf.h btf.h libbpf_common.h libbpf_legacy.h bpf_helpers.h bpf_helper_defs.h bpf_tracing.h bpf_endian.h bpf_core_read.h skel_internal.h libbpf_version.h usdt.bpf.h                                                                                                                                                                                          
defender:   INSTALL  ./libbpf.pc
defender:   INSTALL  ./libbpf.a ./libbpf.so ./libbpf.so.1 ./libbpf.so.1.4.6
defender: make: 'install_headers' is up to date.
defender: ++ ldconfig
defender: ++ grep -q 'PKG_CONFIG_PATH.*usr/lib64/pkgconfig' /etc/environment
defender: ++ echo 'PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"'
defender: ++ cat
defender: ++ chmod +x /etc/profile.d/libbpf.sh
defender: ++ export PKG_CONFIG_PATH=/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:
defender: ++ PKG_CONFIG_PATH=/usr/lib64/pkgconfig:/usr/local/lib/pkgconfig:
defender: ++ export LD_LIBRARY_PATH=/usr/lib64:/usr/local/lib:
defender: ++ LD_LIBRARY_PATH=/usr/lib64:/usr/local/lib:
defender: ++ echo /usr/lib64
defender: ++ ldconfig
defender: ++ cd /tmp
defender: ++ rm -rf libbpf
defender: ++ apt-get install -y libjsoncpp-dev libcurl4-openssl-dev libzmq3-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   comerr-dev cppzmq-dev e2fsprogs krb5-locales krb5-multidev libbsd-dev
defender:   libcom-err2 libext2fs2 libgssapi-krb5-2 libgssrpc4 libjsoncpp25 libk5crypto3
defender:   libkadm5clnt-mit12 libkadm5srv-mit12 libkdb5-10 libkrb5-3 libkrb5-dev
defender:   libkrb5support0 libmd-dev libnorm-dev libnorm1 libpgm-5.3-0 libpgm-dev
defender:   libsodium-dev libss2 libzmq5 logsave
defender: Suggested packages:
defender:   doc-base gpart parted fuse2fs e2fsck-static krb5-doc libcurl4-doc libidn-dev
defender:   libldap2-dev librtmp-dev libssh2-1-dev libssl-dev krb5-user libnorm-doc
defender: Recommended packages:
defender:   e2fsprogs-l10n
defender: The following NEW packages will be installed:
defender:   comerr-dev cppzmq-dev krb5-multidev libbsd-dev libcurl4-openssl-dev
defender:   libgssrpc4 libjsoncpp-dev libjsoncpp25 libkadm5clnt-mit12 libkadm5srv-mit12
defender:   libkdb5-10 libkrb5-dev libmd-dev libnorm-dev libnorm1 libpgm-5.3-0
defender:   libpgm-dev libsodium-dev libzmq3-dev libzmq5
defender: The following packages will be upgraded:
defender:   e2fsprogs krb5-locales libcom-err2 libext2fs2 libgssapi-krb5-2 libk5crypto3
defender:   libkrb5-3 libkrb5support0 libss2 logsave
defender: 10 upgraded, 20 newly installed, 0 to remove and 73 not upgraded.
defender: Need to get 4687 kB of archives.
defender: After this operation, 13.1 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 logsave amd64 1.47.0-2+b2 [19.9 kB]
defender: Get:2 https://security.debian.org/debian-security bookworm-security/main amd64 libsodium-dev amd64 1.0.18-1+deb12u1 [181 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libext2fs2 amd64 1.47.0-2+b2 [205 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 e2fsprogs amd64 1.47.0-2+b2 [572 kB]
defender: Get:5 https://deb.debian.org/debian bookworm/main amd64 krb5-locales all 1.20.1-2+deb12u4 [63.4 kB]
defender: Get:6 https://deb.debian.org/debian bookworm/main amd64 libcom-err2 amd64 1.47.0-2+b2 [20.0 kB]
defender: Get:7 https://deb.debian.org/debian bookworm/main amd64 comerr-dev amd64 2.1-1.47.0-2+b2 [51.7 kB]
defender: Get:8 https://deb.debian.org/debian bookworm/main amd64 libgssapi-krb5-2 amd64 1.20.1-2+deb12u4 [135 kB]
defender: Get:9 https://deb.debian.org/debian bookworm/main amd64 libkrb5-3 amd64 1.20.1-2+deb12u4 [334 kB]
defender: Get:10 https://deb.debian.org/debian bookworm/main amd64 libkrb5support0 amd64 1.20.1-2+deb12u4 [33.2 kB]
defender: Get:11 https://deb.debian.org/debian bookworm/main amd64 libk5crypto3 amd64 1.20.1-2+deb12u4 [79.8 kB]
defender: Get:12 https://deb.debian.org/debian bookworm/main amd64 libnorm1 amd64 1.5.9+dfsg-2 [221 kB]
defender: Get:13 https://deb.debian.org/debian bookworm/main amd64 libpgm-5.3-0 amd64 5.3.128~dfsg-2 [161 kB]
defender: Get:14 https://deb.debian.org/debian bookworm/main amd64 libzmq5 amd64 4.3.4-6 [273 kB]
defender: Get:15 https://deb.debian.org/debian bookworm/main amd64 libpgm-dev amd64 5.3.128~dfsg-2 [194 kB]
defender: Get:16 https://deb.debian.org/debian bookworm/main amd64 libnorm-dev amd64 1.5.9+dfsg-2 [391 kB]
defender: Get:17 https://deb.debian.org/debian bookworm/main amd64 libgssrpc4 amd64 1.20.1-2+deb12u4 [58.7 kB]
defender: Get:18 https://deb.debian.org/debian bookworm/main amd64 libkdb5-10 amd64 1.20.1-2+deb12u4 [41.3 kB]
defender: Get:19 https://deb.debian.org/debian bookworm/main amd64 libkadm5srv-mit12 amd64 1.20.1-2+deb12u4 [53.4 kB]
defender: Get:20 https://deb.debian.org/debian bookworm/main amd64 libkadm5clnt-mit12 amd64 1.20.1-2+deb12u4 [41.6 kB]
defender: Get:21 https://deb.debian.org/debian bookworm/main amd64 krb5-multidev amd64 1.20.1-2+deb12u4 [126 kB]
defender: Get:22 https://deb.debian.org/debian bookworm/main amd64 libkrb5-dev amd64 1.20.1-2+deb12u4 [15.4 kB]
defender: Get:23 https://deb.debian.org/debian bookworm/main amd64 libmd-dev amd64 1.0.4-2 [47.0 kB]
defender: Get:24 https://deb.debian.org/debian bookworm/main amd64 libbsd-dev amd64 0.11.7-2 [243 kB]
defender: Get:25 https://deb.debian.org/debian bookworm/main amd64 libzmq3-dev amd64 4.3.4-6 [479 kB]
defender: Get:26 https://deb.debian.org/debian bookworm/main amd64 cppzmq-dev amd64 4.9.0-1 [25.0 kB]
defender: Get:27 https://deb.debian.org/debian bookworm/main amd64 libcurl4-openssl-dev amd64 7.88.1-10+deb12u14 [492 kB]
defender: Get:28 https://deb.debian.org/debian bookworm/main amd64 libjsoncpp25 amd64 1.9.5-4 [78.6 kB]
defender: Get:29 https://deb.debian.org/debian bookworm/main amd64 libjsoncpp-dev amd64 1.9.5-4 [26.4 kB]
defender: Get:30 https://deb.debian.org/debian bookworm/main amd64 libss2 amd64 1.47.0-2+b2 [24.8 kB]
defender: apt-listchanges: Reading changelogs...
defender: Fetched 4687 kB in 32s (148 kB/s)
(Reading database ... 62246 files and directories currently installed.)
defender: Preparing to unpack .../logsave_1.47.0-2+b2_amd64.deb ...
defender: Unpacking logsave (1.47.0-2+b2) over (1.47.0-2) ...
defender: Preparing to unpack .../libext2fs2_1.47.0-2+b2_amd64.deb ...
defender: Unpacking libext2fs2:amd64 (1.47.0-2+b2) over (1.47.0-2) ...
defender: Setting up libext2fs2:amd64 (1.47.0-2+b2) ...
(Reading database ... 62248 files and directories currently installed.)
defender: Preparing to unpack .../00-e2fsprogs_1.47.0-2+b2_amd64.deb ...
defender: Unpacking e2fsprogs (1.47.0-2+b2) over (1.47.0-2) ...
defender: Preparing to unpack .../01-krb5-locales_1.20.1-2+deb12u4_all.deb ...
defender: Unpacking krb5-locales (1.20.1-2+deb12u4) over (1.20.1-2+deb12u2) ...
defender: Preparing to unpack .../02-libcom-err2_1.47.0-2+b2_amd64.deb ...
defender: Unpacking libcom-err2:amd64 (1.47.0-2+b2) over (1.47.0-2) ...
defender: Selecting previously unselected package comerr-dev:amd64.
defender: Preparing to unpack .../03-comerr-dev_2.1-1.47.0-2+b2_amd64.deb ...
defender: Unpacking comerr-dev:amd64 (2.1-1.47.0-2+b2) ...
defender: Preparing to unpack .../04-libgssapi-krb5-2_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libgssapi-krb5-2:amd64 (1.20.1-2+deb12u4) over (1.20.1-2+deb12u2) ...
defender: Preparing to unpack .../05-libkrb5-3_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libkrb5-3:amd64 (1.20.1-2+deb12u4) over (1.20.1-2+deb12u2) ...
defender: Preparing to unpack .../06-libkrb5support0_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libkrb5support0:amd64 (1.20.1-2+deb12u4) over (1.20.1-2+deb12u2) ...
defender: Preparing to unpack .../07-libk5crypto3_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libk5crypto3:amd64 (1.20.1-2+deb12u4) over (1.20.1-2+deb12u2) ...
defender: Selecting previously unselected package libnorm1:amd64.
defender: Preparing to unpack .../08-libnorm1_1.5.9+dfsg-2_amd64.deb ...
defender: Unpacking libnorm1:amd64 (1.5.9+dfsg-2) ...
defender: Selecting previously unselected package libpgm-5.3-0:amd64.
defender: Preparing to unpack .../09-libpgm-5.3-0_5.3.128~dfsg-2_amd64.deb ...
defender: Unpacking libpgm-5.3-0:amd64 (5.3.128~dfsg-2) ...
defender: Selecting previously unselected package libzmq5:amd64.
defender: Preparing to unpack .../10-libzmq5_4.3.4-6_amd64.deb ...
defender: Unpacking libzmq5:amd64 (4.3.4-6) ...
defender: Selecting previously unselected package libpgm-dev:amd64.
defender: Preparing to unpack .../11-libpgm-dev_5.3.128~dfsg-2_amd64.deb ...
defender: Unpacking libpgm-dev:amd64 (5.3.128~dfsg-2) ...
defender: Selecting previously unselected package libsodium-dev:amd64.
defender: Preparing to unpack .../12-libsodium-dev_1.0.18-1+deb12u1_amd64.deb ...
defender: Unpacking libsodium-dev:amd64 (1.0.18-1+deb12u1) ...
defender: Selecting previously unselected package libnorm-dev:amd64.
defender: Preparing to unpack .../13-libnorm-dev_1.5.9+dfsg-2_amd64.deb ...
defender: Unpacking libnorm-dev:amd64 (1.5.9+dfsg-2) ...
defender: Selecting previously unselected package libgssrpc4:amd64.
defender: Preparing to unpack .../14-libgssrpc4_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libgssrpc4:amd64 (1.20.1-2+deb12u4) ...
defender: Selecting previously unselected package libkdb5-10:amd64.
defender: Preparing to unpack .../15-libkdb5-10_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libkdb5-10:amd64 (1.20.1-2+deb12u4) ...
defender: Selecting previously unselected package libkadm5srv-mit12:amd64.
defender: Preparing to unpack .../16-libkadm5srv-mit12_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libkadm5srv-mit12:amd64 (1.20.1-2+deb12u4) ...
defender: Selecting previously unselected package libkadm5clnt-mit12:amd64.
defender: Preparing to unpack .../17-libkadm5clnt-mit12_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libkadm5clnt-mit12:amd64 (1.20.1-2+deb12u4) ...
defender: Selecting previously unselected package krb5-multidev:amd64.
defender: Preparing to unpack .../18-krb5-multidev_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking krb5-multidev:amd64 (1.20.1-2+deb12u4) ...
defender: Selecting previously unselected package libkrb5-dev:amd64.
defender: Preparing to unpack .../19-libkrb5-dev_1.20.1-2+deb12u4_amd64.deb ...
defender: Unpacking libkrb5-dev:amd64 (1.20.1-2+deb12u4) ...
defender: Selecting previously unselected package libmd-dev:amd64.
defender: Preparing to unpack .../20-libmd-dev_1.0.4-2_amd64.deb ...
defender: Unpacking libmd-dev:amd64 (1.0.4-2) ...
defender: Selecting previously unselected package libbsd-dev:amd64.
defender: Preparing to unpack .../21-libbsd-dev_0.11.7-2_amd64.deb ...
defender: Unpacking libbsd-dev:amd64 (0.11.7-2) ...
defender: Selecting previously unselected package libzmq3-dev:amd64.
defender: Preparing to unpack .../22-libzmq3-dev_4.3.4-6_amd64.deb ...
defender: Unpacking libzmq3-dev:amd64 (4.3.4-6) ...
defender: Selecting previously unselected package cppzmq-dev:amd64.
defender: Preparing to unpack .../23-cppzmq-dev_4.9.0-1_amd64.deb ...
defender: Unpacking cppzmq-dev:amd64 (4.9.0-1) ...
defender: Selecting previously unselected package libcurl4-openssl-dev:amd64.
defender: Preparing to unpack .../24-libcurl4-openssl-dev_7.88.1-10+deb12u14_amd64.deb ...
defender: Unpacking libcurl4-openssl-dev:amd64 (7.88.1-10+deb12u14) ...
defender: Selecting previously unselected package libjsoncpp25:amd64.
defender: Preparing to unpack .../25-libjsoncpp25_1.9.5-4_amd64.deb ...
defender: Unpacking libjsoncpp25:amd64 (1.9.5-4) ...
defender: Selecting previously unselected package libjsoncpp-dev:amd64.
defender: Preparing to unpack .../26-libjsoncpp-dev_1.9.5-4_amd64.deb ...
defender: Unpacking libjsoncpp-dev:amd64 (1.9.5-4) ...
defender: Preparing to unpack .../27-libss2_1.47.0-2+b2_amd64.deb ...
defender: Unpacking libss2:amd64 (1.47.0-2+b2) over (1.47.0-2) ...
defender: Setting up libpgm-5.3-0:amd64 (5.3.128~dfsg-2) ...
defender: Setting up libnorm1:amd64 (1.5.9+dfsg-2) ...
defender: Setting up libnorm-dev:amd64 (1.5.9+dfsg-2) ...
defender: Setting up krb5-locales (1.20.1-2+deb12u4) ...
defender: Setting up libcom-err2:amd64 (1.47.0-2+b2) ...
defender: Setting up libkrb5support0:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libcurl4-openssl-dev:amd64 (7.88.1-10+deb12u14) ...
defender: Setting up libpgm-dev:amd64 (5.3.128~dfsg-2) ...
defender: Setting up comerr-dev:amd64 (2.1-1.47.0-2+b2) ...
defender: Setting up libss2:amd64 (1.47.0-2+b2) ...
defender: Setting up libjsoncpp25:amd64 (1.9.5-4) ...
defender: Setting up libsodium-dev:amd64 (1.0.18-1+deb12u1) ...
defender: Setting up libk5crypto3:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up logsave (1.47.0-2+b2) ...
defender: Setting up libmd-dev:amd64 (1.0.4-2) ...
defender: Setting up libkrb5-3:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libbsd-dev:amd64 (0.11.7-2) ...
defender: Setting up libjsoncpp-dev:amd64 (1.9.5-4) ...
defender: Setting up e2fsprogs (1.47.0-2+b2) ...
defender: update-initramfs: deferring update (trigger activated)
defender: e2scrub_all.service is a disabled or a static unit not running, not starting it.
defender: Setting up libgssapi-krb5-2:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libzmq5:amd64 (4.3.4-6) ...
defender: Setting up libgssrpc4:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libkadm5clnt-mit12:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libkdb5-10:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libkadm5srv-mit12:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up krb5-multidev:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libkrb5-dev:amd64 (1.20.1-2+deb12u4) ...
defender: Setting up libzmq3-dev:amd64 (4.3.4-6) ...
defender: Setting up cppzmq-dev:amd64 (4.9.0-1) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: Processing triggers for initramfs-tools (0.142+deb12u1) ...
defender: update-initramfs: Generating /boot/initrd.img-6.1.0-45-amd64
defender: W: No zstd in /usr/bin:/sbin:/bin, using gzip
defender: ++ apt-get install -y protobuf-compiler libprotobuf-dev libprotobuf32
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   libprotobuf-lite32 libprotoc32
defender: Suggested packages:
defender:   protobuf-mode-el
defender: The following NEW packages will be installed:
defender:   libprotobuf-dev libprotobuf-lite32 libprotobuf32 libprotoc32
defender:   protobuf-compiler
defender: 0 upgraded, 5 newly installed, 0 to remove and 73 not upgraded.
defender: Need to get 3390 kB of archives.
defender: After this operation, 19.6 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 libprotobuf32 amd64 3.21.12-3 [932 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libprotobuf-lite32 amd64 3.21.12-3 [261 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libprotobuf-dev amd64 3.21.12-3 [1283 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 libprotoc32 amd64 3.21.12-3 [829 kB]
defender: Get:5 https://deb.debian.org/debian bookworm/main amd64 protobuf-compiler amd64 3.21.12-3 [83.9 kB]
defender: Fetched 3390 kB in 1s (3370 kB/s)
defender: Selecting previously unselected package libprotobuf32:amd64.
(Reading database ... 63088 files and directories currently installed.)
defender: Preparing to unpack .../libprotobuf32_3.21.12-3_amd64.deb ...
defender: Unpacking libprotobuf32:amd64 (3.21.12-3) ...
defender: Selecting previously unselected package libprotobuf-lite32:amd64.
defender: Preparing to unpack .../libprotobuf-lite32_3.21.12-3_amd64.deb ...
defender: Unpacking libprotobuf-lite32:amd64 (3.21.12-3) ...
defender: Selecting previously unselected package libprotobuf-dev:amd64.
defender: Preparing to unpack .../libprotobuf-dev_3.21.12-3_amd64.deb ...
defender: Unpacking libprotobuf-dev:amd64 (3.21.12-3) ...
defender: Selecting previously unselected package libprotoc32:amd64.
defender: Preparing to unpack .../libprotoc32_3.21.12-3_amd64.deb ...
defender: Unpacking libprotoc32:amd64 (3.21.12-3) ...
defender: Selecting previously unselected package protobuf-compiler.
defender: Preparing to unpack .../protobuf-compiler_3.21.12-3_amd64.deb ...
defender: Unpacking protobuf-compiler (3.21.12-3) ...
defender: Setting up libprotobuf32:amd64 (3.21.12-3) ...
defender: Setting up libprotobuf-lite32:amd64 (3.21.12-3) ...
defender: Setting up libprotoc32:amd64 (3.21.12-3) ...
defender: Setting up protobuf-compiler (3.21.12-3) ...
defender: Setting up libprotobuf-dev:amd64 (3.21.12-3) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: ++ apt-get install -y liblz4-dev libzstd-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following NEW packages will be installed:
defender:   liblz4-dev libzstd-dev
defender: 0 upgraded, 2 newly installed, 0 to remove and 73 not upgraded.
defender: Need to get 438 kB of archives.
defender: After this operation, 1538 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 liblz4-dev amd64 1.9.4-1 [84.3 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libzstd-dev amd64 1.5.4+dfsg2-5 [354 kB]
defender: Fetched 438 kB in 0s (1489 kB/s)
defender: Selecting previously unselected package liblz4-dev:amd64.
(Reading database ... 63259 files and directories currently installed.)
defender: Preparing to unpack .../liblz4-dev_1.9.4-1_amd64.deb ...
defender: Unpacking liblz4-dev:amd64 (1.9.4-1) ...
defender: Selecting previously unselected package libzstd-dev:amd64.
defender: Preparing to unpack .../libzstd-dev_1.5.4+dfsg2-5_amd64.deb ...
defender: Unpacking libzstd-dev:amd64 (1.5.4+dfsg2-5) ...
defender: Setting up libzstd-dev:amd64 (1.5.4+dfsg2-5) ...
defender: Setting up liblz4-dev:amd64 (1.9.4-1) ...
defender: ++ apt-get install -y pkg-config libspdlog-dev nlohmann-json3-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: pkg-config is already the newest version (1.8.1-1).
defender: The following additional packages will be installed:
defender:   catch2 libfmt-dev libfmt9 libspdlog1.10
defender: Suggested packages:
defender:   libfmt-doc
defender: The following NEW packages will be installed:
defender:   catch2 libfmt-dev libfmt9 libspdlog-dev libspdlog1.10 nlohmann-json3-dev
defender: 0 upgraded, 6 newly installed, 0 to remove and 73 not upgraded.
defender: Need to get 1340 kB of archives.
defender: After this operation, 6248 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 catch2 amd64 2.13.10-1 [458 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libfmt9 amd64 9.1.0+ds1-2 [113 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libfmt-dev amd64 9.1.0+ds1-2 [171 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 libspdlog1.10 amd64 1:1.10.0+ds-0.4 [130 kB]
defender: Get:5 https://deb.debian.org/debian bookworm/main amd64 libspdlog-dev amd64 1:1.10.0+ds-0.4 [209 kB]
defender: Get:6 https://deb.debian.org/debian bookworm/main amd64 nlohmann-json3-dev all 3.11.2-2 [259 kB]
defender: Fetched 1340 kB in 1s (2631 kB/s)
defender: Selecting previously unselected package catch2.
(Reading database ... 63299 files and directories currently installed.)
defender: Preparing to unpack .../0-catch2_2.13.10-1_amd64.deb ...
defender: Unpacking catch2 (2.13.10-1) ...
defender: Selecting previously unselected package libfmt9:amd64.
defender: Preparing to unpack .../1-libfmt9_9.1.0+ds1-2_amd64.deb ...
defender: Unpacking libfmt9:amd64 (9.1.0+ds1-2) ...
defender: Selecting previously unselected package libfmt-dev:amd64.
defender: Preparing to unpack .../2-libfmt-dev_9.1.0+ds1-2_amd64.deb ...
defender: Unpacking libfmt-dev:amd64 (9.1.0+ds1-2) ...
defender: Selecting previously unselected package libspdlog1.10:amd64.
defender: Preparing to unpack .../3-libspdlog1.10_1%3a1.10.0+ds-0.4_amd64.deb ...
defender: Unpacking libspdlog1.10:amd64 (1:1.10.0+ds-0.4) ...
defender: Selecting previously unselected package libspdlog-dev:amd64.
defender: Preparing to unpack .../4-libspdlog-dev_1%3a1.10.0+ds-0.4_amd64.deb ...
defender: Unpacking libspdlog-dev:amd64 (1:1.10.0+ds-0.4) ...
defender: Selecting previously unselected package nlohmann-json3-dev.
defender: Preparing to unpack .../5-nlohmann-json3-dev_3.11.2-2_all.deb ...
defender: Unpacking nlohmann-json3-dev (3.11.2-2) ...
defender: Setting up catch2 (2.13.10-1) ...
defender: Setting up libfmt9:amd64 (9.1.0+ds1-2) ...
defender: Setting up nlohmann-json3-dev (3.11.2-2) ...
defender: Setting up libspdlog1.10:amd64 (1:1.10.0+ds-0.4) ...
defender: Setting up libfmt-dev:amd64 (9.1.0+ds1-2) ...
defender: Setting up libspdlog-dev:amd64 (1:1.10.0+ds-0.4) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: ++ apt-get install -y iptables ipset libxtables-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: iptables is already the newest version (1.8.9-2).
defender: The following NEW packages will be installed:
defender:   ipset libipset13 libxtables-dev
defender: 0 upgraded, 3 newly installed, 0 to remove and 73 not upgraded.
defender: Need to get 126 kB of archives.
defender: After this operation, 467 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 libipset13 amd64 7.17-1 [67.5 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 ipset amd64 7.17-1 [45.7 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libxtables-dev amd64 1.8.9-2 [13.2 kB]
defender: Fetched 126 kB in 0s (771 kB/s)
defender: Selecting previously unselected package libipset13:amd64.
(Reading database ... 64022 files and directories currently installed.)
defender: Preparing to unpack .../libipset13_7.17-1_amd64.deb ...
defender: Unpacking libipset13:amd64 (7.17-1) ...
defender: Selecting previously unselected package ipset.
defender: Preparing to unpack .../ipset_7.17-1_amd64.deb ...
defender: Unpacking ipset (7.17-1) ...
defender: Selecting previously unselected package libxtables-dev:amd64.
defender: Preparing to unpack .../libxtables-dev_1.8.9-2_amd64.deb ...
defender: Unpacking libxtables-dev:amd64 (1.8.9-2) ...
defender: Setting up libxtables-dev:amd64 (1.8.9-2) ...
defender: Setting up libipset13:amd64 (7.17-1) ...
defender: Setting up ipset (7.17-1) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: ++ apt-get install -y apparmor-utils apparmor-profiles
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   python3-apparmor python3-libapparmor
defender: Suggested packages:
defender:   vim-addon-manager
defender: The following NEW packages will be installed:
defender:   apparmor-profiles apparmor-utils python3-apparmor python3-libapparmor
defender: 0 upgraded, 4 newly installed, 0 to remove and 73 not upgraded.
defender: Need to get 260 kB of archives.
defender: After this operation, 1335 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 apparmor-profiles all 3.0.8-3 [41.7 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 python3-libapparmor amd64 3.0.8-3 [36.4 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 python3-apparmor all 3.0.8-3 [87.8 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 apparmor-utils all 3.0.8-3 [94.0 kB]
defender: Fetched 260 kB in 0s (1055 kB/s)
defender: Selecting previously unselected package apparmor-profiles.
(Reading database ... 64048 files and directories currently installed.)
defender: Preparing to unpack .../apparmor-profiles_3.0.8-3_all.deb ...
defender: Unpacking apparmor-profiles (3.0.8-3) ...
defender: Selecting previously unselected package python3-libapparmor.
defender: Preparing to unpack .../python3-libapparmor_3.0.8-3_amd64.deb ...
defender: Unpacking python3-libapparmor (3.0.8-3) ...
defender: Selecting previously unselected package python3-apparmor.
defender: Preparing to unpack .../python3-apparmor_3.0.8-3_all.deb ...
defender: Unpacking python3-apparmor (3.0.8-3) ...
defender: Selecting previously unselected package apparmor-utils.
defender: Preparing to unpack .../apparmor-utils_3.0.8-3_all.deb ...
defender: Unpacking apparmor-utils (3.0.8-3) ...
defender: Setting up python3-libapparmor (3.0.8-3) ...
defender: Setting up apparmor-profiles (3.0.8-3) ...
defender: Setting up python3-apparmor (3.0.8-3) ...
defender: Setting up apparmor-utils (3.0.8-3) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: ++ apt-get install -y libboost-all-dev libtool autoconf automake libgrpc-dev libgrpc++-dev protobuf-compiler-grpc libc-ares-dev libre2-dev libabsl-dev libbenchmark-dev libgtest-dev libssl-dev libcpprest-dev cmake                                                                                                                                                            
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   autotools-dev cmake-data gfortran gfortran-12 googletest ibverbs-providers
defender:   javascript-common libarchive13 libbenchmark1debian libboost-atomic-dev
defender:   libboost-atomic1.74-dev libboost-atomic1.74.0 libboost-chrono-dev
defender:   libboost-chrono1.74-dev libboost-chrono1.74.0 libboost-container-dev
defender:   libboost-container1.74-dev libboost-container1.74.0 libboost-context-dev
defender:   libboost-context1.74-dev libboost-context1.74.0 libboost-coroutine-dev
defender:   libboost-coroutine1.74-dev libboost-coroutine1.74.0 libboost-date-time-dev
defender:   libboost-date-time1.74-dev libboost-date-time1.74.0 libboost-dev
defender:   libboost-exception-dev libboost-exception1.74-dev libboost-fiber-dev
defender:   libboost-fiber1.74-dev libboost-fiber1.74.0 libboost-filesystem-dev
defender:   libboost-filesystem1.74-dev libboost-filesystem1.74.0 libboost-graph-dev
defender:   libboost-graph-parallel-dev libboost-graph-parallel1.74-dev
defender:   libboost-graph-parallel1.74.0 libboost-graph1.74-dev libboost-graph1.74.0
defender:   libboost-iostreams-dev libboost-iostreams1.74-dev libboost-iostreams1.74.0
defender:   libboost-locale-dev libboost-locale1.74-dev libboost-locale1.74.0
defender:   libboost-log-dev libboost-log1.74-dev libboost-log1.74.0 libboost-math-dev
defender:   libboost-math1.74-dev libboost-math1.74.0 libboost-mpi-dev
defender:   libboost-mpi-python-dev libboost-mpi-python1.74-dev
defender:   libboost-mpi-python1.74.0 libboost-mpi1.74-dev libboost-mpi1.74.0
defender:   libboost-nowide-dev libboost-nowide1.74-dev libboost-nowide1.74.0
defender:   libboost-numpy-dev libboost-numpy1.74-dev libboost-numpy1.74.0
defender:   libboost-program-options-dev libboost-program-options1.74-dev
defender:   libboost-program-options1.74.0 libboost-python-dev libboost-python1.74-dev
defender:   libboost-python1.74.0 libboost-random-dev libboost-random1.74-dev
defender:   libboost-random1.74.0 libboost-regex-dev libboost-regex1.74-dev
defender:   libboost-regex1.74.0 libboost-serialization-dev
defender:   libboost-serialization1.74-dev libboost-serialization1.74.0
defender:   libboost-stacktrace-dev libboost-stacktrace1.74-dev
defender:   libboost-stacktrace1.74.0 libboost-system-dev libboost-system1.74-dev
defender:   libboost-system1.74.0 libboost-test-dev libboost-test1.74-dev
defender:   libboost-test1.74.0 libboost-thread-dev libboost-thread1.74-dev
defender:   libboost-thread1.74.0 libboost-timer-dev libboost-timer1.74-dev
defender:   libboost-timer1.74.0 libboost-tools-dev libboost-type-erasure-dev
defender:   libboost-type-erasure1.74-dev libboost-type-erasure1.74.0 libboost-wave-dev
defender:   libboost-wave1.74-dev libboost-wave1.74.0 libboost1.74-dev
defender:   libboost1.74-tools-dev libbrotli-dev libc-ares2 libcaf-openmpi-3
defender:   libcoarrays-dev libcoarrays-openmpi-dev libcpprest2.10 libevent-2.1-7
defender:   libevent-dev libevent-extra-2.1-7 libevent-openssl-2.1-7
defender:   libevent-pthreads-2.1-7 libexpat1 libexpat1-dev libfabric1
defender:   libgfortran-12-dev libgfortran5 libgrpc++1.51 libgrpc29 libhwloc-dev
defender:   libhwloc-plugins libhwloc15 libibverbs-dev libibverbs1 libjs-jquery
defender:   libjs-jquery-ui libjs-sphinxdoc libjs-underscore libltdl-dev libltdl7
defender:   libmunge2 libnl-3-200 libnl-3-dev libnl-route-3-200 libnl-route-3-dev
defender:   libnuma-dev libopenmpi-dev libopenmpi3 libpciaccess0 libpmix-dev libpmix2
defender:   libpsm-infinipath1 libpsm2-2 libpython3-dev libpython3.11 libpython3.11-dev
defender:   libpython3.11-minimal libpython3.11-stdlib librdmacm1 libre2-9 librhash0
defender:   libssl3 libucx0 libwebsocketpp-dev libxext6 libxnvctrl0 m4 mpi-default-bin
defender:   mpi-default-dev ocl-icd-libopencl1 openmpi-bin openmpi-common openssl
defender:   python3-dev python3-distutils python3-lib2to3 python3.11 python3.11-dev
defender:   python3.11-minimal
defender: Suggested packages:
defender:   autoconf-archive gnu-standards autoconf-doc gettext cmake-doc cmake-format
defender:   elpa-cmake-mode ninja-build gfortran-multilib gfortran-doc
defender:   gfortran-12-multilib gfortran-12-doc apache2 | lighttpd | httpd lrzip
defender:   libbenchmark-tools libboost-doc graphviz libboost1.74-doc gccxml
defender:   libboost-contract1.74-dev libmpfrc++-dev libntl-dev xsltproc doxygen
defender:   docbook-xml docbook-xsl default-jdk fop libhwloc-contrib-plugins
defender:   libjs-jquery-ui-docs libtool-doc openmpi-doc libssl-doc gcj-jdk m4-doc
defender:   opencl-icd python3.11-venv python3.11-doc binfmt-support
defender: The following NEW packages will be installed:
defender:   autoconf automake autotools-dev cmake cmake-data gfortran gfortran-12
defender:   googletest ibverbs-providers javascript-common libabsl-dev libarchive13
defender:   libbenchmark-dev libbenchmark1debian libboost-all-dev libboost-atomic-dev
defender:   libboost-atomic1.74-dev libboost-atomic1.74.0 libboost-chrono-dev
defender:   libboost-chrono1.74-dev libboost-chrono1.74.0 libboost-container-dev
defender:   libboost-container1.74-dev libboost-container1.74.0 libboost-context-dev
defender:   libboost-context1.74-dev libboost-context1.74.0 libboost-coroutine-dev
defender:   libboost-coroutine1.74-dev libboost-coroutine1.74.0 libboost-date-time-dev
defender:   libboost-date-time1.74-dev libboost-date-time1.74.0 libboost-dev
defender:   libboost-exception-dev libboost-exception1.74-dev libboost-fiber-dev
defender:   libboost-fiber1.74-dev libboost-fiber1.74.0 libboost-filesystem-dev
defender:   libboost-filesystem1.74-dev libboost-filesystem1.74.0 libboost-graph-dev
defender:   libboost-graph-parallel-dev libboost-graph-parallel1.74-dev
defender:   libboost-graph-parallel1.74.0 libboost-graph1.74-dev libboost-graph1.74.0
defender:   libboost-iostreams-dev libboost-iostreams1.74-dev libboost-iostreams1.74.0
defender:   libboost-locale-dev libboost-locale1.74-dev libboost-locale1.74.0
defender:   libboost-log-dev libboost-log1.74-dev libboost-log1.74.0 libboost-math-dev
defender:   libboost-math1.74-dev libboost-math1.74.0 libboost-mpi-dev
defender:   libboost-mpi-python-dev libboost-mpi-python1.74-dev
defender:   libboost-mpi-python1.74.0 libboost-mpi1.74-dev libboost-mpi1.74.0
defender:   libboost-nowide-dev libboost-nowide1.74-dev libboost-nowide1.74.0
defender:   libboost-numpy-dev libboost-numpy1.74-dev libboost-numpy1.74.0
defender:   libboost-program-options-dev libboost-program-options1.74-dev
defender:   libboost-program-options1.74.0 libboost-python-dev libboost-python1.74-dev
defender:   libboost-python1.74.0 libboost-random-dev libboost-random1.74-dev
defender:   libboost-random1.74.0 libboost-regex-dev libboost-regex1.74-dev
defender:   libboost-regex1.74.0 libboost-serialization-dev
defender:   libboost-serialization1.74-dev libboost-serialization1.74.0
defender:   libboost-stacktrace-dev libboost-stacktrace1.74-dev
defender:   libboost-stacktrace1.74.0 libboost-system-dev libboost-system1.74-dev
defender:   libboost-system1.74.0 libboost-test-dev libboost-test1.74-dev
defender:   libboost-test1.74.0 libboost-thread-dev libboost-thread1.74-dev
defender:   libboost-thread1.74.0 libboost-timer-dev libboost-timer1.74-dev
defender:   libboost-timer1.74.0 libboost-tools-dev libboost-type-erasure-dev
defender:   libboost-type-erasure1.74-dev libboost-type-erasure1.74.0 libboost-wave-dev
defender:   libboost-wave1.74-dev libboost-wave1.74.0 libboost1.74-dev
defender:   libboost1.74-tools-dev libbrotli-dev libc-ares-dev libc-ares2
defender:   libcaf-openmpi-3 libcoarrays-dev libcoarrays-openmpi-dev libcpprest-dev
defender:   libcpprest2.10 libevent-2.1-7 libevent-dev libevent-extra-2.1-7
defender:   libevent-openssl-2.1-7 libevent-pthreads-2.1-7 libexpat1-dev libfabric1
defender:   libgfortran-12-dev libgfortran5 libgrpc++-dev libgrpc++1.51 libgrpc-dev
defender:   libgrpc29 libgtest-dev libhwloc-dev libhwloc-plugins libhwloc15
defender:   libibverbs-dev libibverbs1 libjs-jquery libjs-jquery-ui libjs-sphinxdoc
defender:   libjs-underscore libltdl-dev libltdl7 libmunge2 libnl-3-200 libnl-3-dev
defender:   libnl-route-3-200 libnl-route-3-dev libnuma-dev libopenmpi-dev libopenmpi3
defender:   libpciaccess0 libpmix-dev libpmix2 libpsm-infinipath1 libpsm2-2
defender:   libpython3-dev libpython3.11 libpython3.11-dev librdmacm1 libre2-9
defender:   libre2-dev librhash0 libssl-dev libtool libucx0 libwebsocketpp-dev libxext6
defender:   libxnvctrl0 m4 mpi-default-bin mpi-default-dev ocl-icd-libopencl1
defender:   openmpi-bin openmpi-common protobuf-compiler-grpc python3-dev
defender:   python3-distutils python3-lib2to3 python3.11-dev
defender: The following packages will be upgraded:
defender:   libexpat1 libpython3.11-minimal libpython3.11-stdlib libssl3 openssl
defender:   python3.11 python3.11-minimal
defender: 7 upgraded, 181 newly installed, 0 to remove and 66 not upgraded.
defender: Need to get 99.6 MB of archives.
defender: After this operation, 608 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 python3.11 amd64 3.11.2-6+deb12u6 [573 kB]
defender: Get:2 https://security.debian.org/debian-security bookworm-security/main amd64 libssl3 amd64 3.0.19-1~deb12u2 [2032 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libpython3.11-stdlib amd64 3.11.2-6+deb12u6 [1798 kB]
defender: Get:4 https://security.debian.org/debian-security bookworm-security/main amd64 libmunge2 amd64 0.5.15-2+deb12u1 [19.7 kB]
defender: Get:5 https://security.debian.org/debian-security bookworm-security/main amd64 libssl-dev amd64 3.0.19-1~deb12u2 [2441 kB]
defender: Get:6 https://deb.debian.org/debian bookworm/main amd64 python3.11-minimal amd64 3.11.2-6+deb12u6 [2064 kB]
defender: Get:7 https://deb.debian.org/debian bookworm/main amd64 libpython3.11-minimal amd64 3.11.2-6+deb12u6 [817 kB]
defender: Get:8 https://security.debian.org/debian-security bookworm-security/main amd64 openssl amd64 3.0.19-1~deb12u2 [1435 kB]
defender: Get:9 https://deb.debian.org/debian bookworm/main amd64 libexpat1 amd64 2.5.0-1+deb12u2 [99.9 kB]
defender: Get:10 https://deb.debian.org/debian bookworm/main amd64 m4 amd64 1.4.19-3 [287 kB]
defender: Get:11 https://deb.debian.org/debian bookworm/main amd64 autoconf all 2.71-3 [332 kB]
defender: Get:12 https://deb.debian.org/debian bookworm/main amd64 autotools-dev all 20220109.1 [51.6 kB]
defender: Get:13 https://deb.debian.org/debian bookworm/main amd64 automake all 1:1.16.5-1.3 [823 kB]
defender: Get:14 https://deb.debian.org/debian bookworm/main amd64 libarchive13 amd64 3.6.2-1+deb12u3 [343 kB]
defender: Get:15 https://deb.debian.org/debian bookworm/main amd64 librhash0 amd64 1.4.3-3 [134 kB]
defender: Get:16 https://deb.debian.org/debian bookworm/main amd64 cmake-data all 3.25.1-1 [2026 kB]
defender: Get:17 https://deb.debian.org/debian bookworm/main amd64 cmake amd64 3.25.1-1 [8692 kB]
defender: Get:18 https://deb.debian.org/debian bookworm/main amd64 libgfortran5 amd64 12.2.0-14+deb12u1 [793 kB]
defender: Get:19 https://deb.debian.org/debian bookworm/main amd64 libgfortran-12-dev amd64 12.2.0-14+deb12u1 [834 kB]
defender: Get:20 https://deb.debian.org/debian bookworm/main amd64 gfortran-12 amd64 12.2.0-14+deb12u1 [10.2 MB]
defender: Get:21 https://deb.debian.org/debian bookworm/main amd64 gfortran amd64 4:12.2.0-3 [1428 B]
defender: Get:22 https://deb.debian.org/debian bookworm/main amd64 googletest all 1.12.1-0.2 [506 kB]
defender: Get:23 https://deb.debian.org/debian bookworm/main amd64 libnl-3-200 amd64 3.7.0-0.2+b1 [63.1 kB]
defender: Get:24 https://deb.debian.org/debian bookworm/main amd64 libnl-route-3-200 amd64 3.7.0-0.2+b1 [185 kB]
defender: Get:25 https://deb.debian.org/debian bookworm/main amd64 libibverbs1 amd64 44.0-2 [60.7 kB]
defender: Get:26 https://deb.debian.org/debian bookworm/main amd64 ibverbs-providers amd64 44.0-2 [335 kB]
defender: Get:27 https://deb.debian.org/debian bookworm/main amd64 javascript-common all 11+nmu1 [6260 B]
defender: Get:28 https://deb.debian.org/debian bookworm/main amd64 libabsl-dev amd64 20220623.1-1+deb12u2 [973 kB]
defender: Get:29 https://deb.debian.org/debian bookworm/main amd64 libbenchmark1debian amd64 1.7.1-1 [124 kB]
defender: Get:30 https://deb.debian.org/debian bookworm/main amd64 libbenchmark-dev amd64 1.7.1-1 [51.5 kB]
defender: Get:31 https://deb.debian.org/debian bookworm/main amd64 libboost1.74-dev amd64 1.74.0+ds1-21 [9508 kB]
defender: Get:32 https://deb.debian.org/debian bookworm/main amd64 libboost-dev amd64 1.74.0.3 [4548 B]
defender: Get:33 https://deb.debian.org/debian bookworm/main amd64 libboost1.74-tools-dev amd64 1.74.0+ds1-21 [1428 kB]
defender: Get:34 https://deb.debian.org/debian bookworm/main amd64 libboost-tools-dev amd64 1.74.0.3 [4508 B]
defender: Get:35 https://deb.debian.org/debian bookworm/main amd64 libboost-atomic1.74.0 amd64 1.74.0+ds1-21 [220 kB]
defender: Get:36 https://deb.debian.org/debian bookworm/main amd64 libboost-atomic1.74-dev amd64 1.74.0+ds1-21 [221 kB]
defender: Get:37 https://deb.debian.org/debian bookworm/main amd64 libboost-atomic-dev amd64 1.74.0.3 [4640 B]
defender: Get:38 https://deb.debian.org/debian bookworm/main amd64 libboost-chrono1.74.0 amd64 1.74.0+ds1-21 [228 kB]
defender: Get:39 https://deb.debian.org/debian bookworm/main amd64 libboost-chrono1.74-dev amd64 1.74.0+ds1-21 [235 kB]
defender: Get:40 https://deb.debian.org/debian bookworm/main amd64 libboost-chrono-dev amd64 1.74.0.3 [4960 B]
defender: Get:41 https://deb.debian.org/debian bookworm/main amd64 libboost-container1.74.0 amd64 1.74.0+ds1-21 [246 kB]
defender: Get:42 https://deb.debian.org/debian bookworm/main amd64 libboost-container1.74-dev amd64 1.74.0+ds1-21 [250 kB]
defender: Get:43 https://deb.debian.org/debian bookworm/main amd64 libboost-container-dev amd64 1.74.0.3 [4812 B]
defender: Get:44 https://deb.debian.org/debian bookworm/main amd64 libboost-date-time1.74.0 amd64 1.74.0+ds1-21 [217 kB]
defender: Get:45 https://deb.debian.org/debian bookworm/main amd64 libboost-serialization1.74.0 amd64 1.74.0+ds1-21 [317 kB]
defender: Get:46 https://deb.debian.org/debian bookworm/main amd64 libboost-serialization1.74-dev amd64 1.74.0+ds1-21 [359 kB]
defender: Get:47 https://deb.debian.org/debian bookworm/main amd64 libboost-date-time1.74-dev amd64 1.74.0+ds1-21 [226 kB]
defender: Get:48 https://deb.debian.org/debian bookworm/main amd64 libboost-system1.74.0 amd64 1.74.0+ds1-21 [218 kB]
defender: Get:49 https://deb.debian.org/debian bookworm/main amd64 libboost-system1.74-dev amd64 1.74.0+ds1-21 [219 kB]
defender: Get:50 https://deb.debian.org/debian bookworm/main amd64 libboost-thread1.74.0 amd64 1.74.0+ds1-21 [257 kB]
defender: Get:51 https://deb.debian.org/debian bookworm/main amd64 libboost-thread1.74-dev amd64 1.74.0+ds1-21 [267 kB]
defender: Get:52 https://deb.debian.org/debian bookworm/main amd64 libboost-context1.74.0 amd64 1.74.0+ds1-21 [219 kB]
defender: Get:53 https://deb.debian.org/debian bookworm/main amd64 libboost-context1.74-dev amd64 1.74.0+ds1-21 [220 kB]
defender: Get:54 https://deb.debian.org/debian bookworm/main amd64 libboost-context-dev amd64 1.74.0.3 [4540 B]
defender: Get:55 https://deb.debian.org/debian bookworm/main amd64 libboost-coroutine1.74.0 amd64 1.74.0+ds1-21 [234 kB]
defender: Get:56 https://deb.debian.org/debian bookworm/main amd64 libboost-coroutine1.74-dev amd64 1.74.0+ds1-21 [241 kB]
defender: Get:57 https://deb.debian.org/debian bookworm/main amd64 libboost-coroutine-dev amd64 1.74.0.3 [4608 B]
defender: Get:58 https://deb.debian.org/debian bookworm/main amd64 libboost-date-time-dev amd64 1.74.0.3 [4332 B]
defender: Get:59 https://deb.debian.org/debian bookworm/main amd64 libboost-exception1.74-dev amd64 1.74.0+ds1-21 [217 kB]
defender: Get:60 https://deb.debian.org/debian bookworm/main amd64 libboost-exception-dev amd64 1.74.0.3 [4320 B]
defender: Get:61 https://deb.debian.org/debian bookworm/main amd64 libboost-filesystem1.74.0 amd64 1.74.0+ds1-21 [258 kB]
defender: Get:62 https://deb.debian.org/debian bookworm/main amd64 libboost-filesystem1.74-dev amd64 1.74.0+ds1-21 [279 kB]
defender: Get:63 https://deb.debian.org/debian bookworm/main amd64 libboost-fiber1.74.0 amd64 1.74.0+ds1-21 [240 kB]
defender: Get:64 https://deb.debian.org/debian bookworm/main amd64 libboost-fiber1.74-dev amd64 1.74.0+ds1-21 [251 kB]
defender: Get:65 https://deb.debian.org/debian bookworm/main amd64 libboost-fiber-dev amd64 1.74.0.3 [4764 B]
defender: Get:66 https://deb.debian.org/debian bookworm/main amd64 libboost-filesystem-dev amd64 1.74.0.3 [4368 B]
defender: Get:67 https://deb.debian.org/debian bookworm/main amd64 libboost-regex1.74.0 amd64 1.74.0+ds1-21 [487 kB]
defender: Get:68 https://deb.debian.org/debian bookworm/main amd64 libboost-graph1.74.0 amd64 1.74.0+ds1-21 [301 kB]
defender: Get:69 https://deb.debian.org/debian bookworm/main amd64 libboost-regex1.74-dev amd64 1.74.0+ds1-21 [557 kB]
defender: Get:70 https://deb.debian.org/debian bookworm/main amd64 libboost-test1.74.0 amd64 1.74.0+ds1-21 [453 kB]
defender: Get:71 https://deb.debian.org/debian bookworm/main amd64 libboost-test1.74-dev amd64 1.74.0+ds1-21 [526 kB]
defender: Get:72 https://deb.debian.org/debian bookworm/main amd64 libboost-graph1.74-dev amd64 1.74.0+ds1-21 [1480 kB]
defender: Get:73 https://deb.debian.org/debian bookworm/main amd64 libboost-graph-dev amd64 1.74.0.3 [4436 B]
defender: Get:74 https://deb.debian.org/debian bookworm/main amd64 libevent-pthreads-2.1-7 amd64 2.1.12-stable-8 [53.6 kB]
defender: Get:75 https://deb.debian.org/debian bookworm/main amd64 libpsm-infinipath1 amd64 3.3+20.604758e7-6.2 [168 kB]
defender: Get:76 https://deb.debian.org/debian bookworm/main amd64 libpsm2-2 amd64 11.2.185-2 [180 kB]
defender: Get:77 https://deb.debian.org/debian bookworm/main amd64 librdmacm1 amd64 44.0-2 [68.6 kB]
defender: Get:78 https://deb.debian.org/debian bookworm/main amd64 libfabric1 amd64 1.17.0-3 [627 kB]
defender: Get:79 https://deb.debian.org/debian bookworm/main amd64 libhwloc15 amd64 2.9.0-1 [154 kB]
defender: Get:80 https://deb.debian.org/debian bookworm/main amd64 libpciaccess0 amd64 0.17-2 [51.4 kB]
defender: Get:81 https://deb.debian.org/debian bookworm/main amd64 libxext6 amd64 2:1.3.4-1+b1 [52.9 kB]
defender: Get:82 https://deb.debian.org/debian bookworm/main amd64 libxnvctrl0 amd64 525.85.05-3~deb12u1 [13.5 kB]
defender: Get:83 https://deb.debian.org/debian bookworm/main amd64 ocl-icd-libopencl1 amd64 2.3.1-1 [43.0 kB]
defender: Get:84 https://deb.debian.org/debian bookworm/main amd64 libhwloc-plugins amd64 2.9.0-1 [17.5 kB]
defender: Get:85 https://deb.debian.org/debian bookworm/main amd64 libpmix2 amd64 4.2.2-1+deb12u1 [622 kB]
defender: Get:86 https://deb.debian.org/debian bookworm/main amd64 libucx0 amd64 1.13.1-1 [860 kB]
defender: Get:87 https://deb.debian.org/debian bookworm/main amd64 libopenmpi3 amd64 4.1.4-3+b1 [2422 kB]
defender: Get:88 https://deb.debian.org/debian bookworm/main amd64 libboost-mpi1.74.0 amd64 1.74.0+ds1-21 [258 kB]
defender: Get:89 https://deb.debian.org/debian bookworm/main amd64 libboost-graph-parallel1.74.0 amd64 1.74.0+ds1-21 [266 kB]
defender: Get:90 https://deb.debian.org/debian bookworm/main amd64 libboost-graph-parallel1.74-dev amd64 1.74.0+ds1-21 [271 kB]
defender: Get:91 https://deb.debian.org/debian bookworm/main amd64 libboost-graph-parallel-dev amd64 1.74.0.3 [4460 B]
defender: Get:92 https://deb.debian.org/debian bookworm/main amd64 libboost-iostreams1.74.0 amd64 1.74.0+ds1-21 [240 kB]
defender: Get:93 https://deb.debian.org/debian bookworm/main amd64 libboost-iostreams1.74-dev amd64 1.74.0+ds1-21 [248 kB]
defender: Get:94 https://deb.debian.org/debian bookworm/main amd64 libboost-iostreams-dev amd64 1.74.0.3 [4316 B]
defender: Get:95 https://deb.debian.org/debian bookworm/main amd64 libboost-locale1.74.0 amd64 1.74.0+ds1-21 [449 kB]
defender: Get:96 https://deb.debian.org/debian bookworm/main amd64 libboost-locale1.74-dev amd64 1.74.0+ds1-21 [551 kB]
defender: Get:97 https://deb.debian.org/debian bookworm/main amd64 libboost-locale-dev amd64 1.74.0.3 [4660 B]
defender: Get:98 https://deb.debian.org/debian bookworm/main amd64 libboost-log1.74.0 amd64 1.74.0+ds1-21 [599 kB]
defender: Get:99 https://deb.debian.org/debian bookworm/main amd64 libboost-log1.74-dev amd64 1.74.0+ds1-21 [784 kB]
defender: Get:100 https://deb.debian.org/debian bookworm/main amd64 libboost-log-dev amd64 1.74.0.3 [4540 B]
defender: Get:101 https://deb.debian.org/debian bookworm/main amd64 libboost-math1.74.0 amd64 1.74.0+ds1-21 [490 kB]
defender: Get:102 https://deb.debian.org/debian bookworm/main amd64 libboost-math1.74-dev amd64 1.74.0+ds1-21 [564 kB]
defender: Get:103 https://deb.debian.org/debian bookworm/main amd64 libboost-math-dev amd64 1.74.0.3 [4532 B]
defender: Get:104 https://deb.debian.org/debian bookworm/main amd64 openmpi-common all 4.1.4-3 [167 kB]
defender: Get:105 https://deb.debian.org/debian bookworm/main amd64 libnl-3-dev amd64 3.7.0-0.2+b1 [104 kB]
defender: Get:106 https://deb.debian.org/debian bookworm/main amd64 libnl-route-3-dev amd64 3.7.0-0.2+b1 [203 kB]
defender: Get:107 https://deb.debian.org/debian bookworm/main amd64 libibverbs-dev amd64 44.0-2 [633 kB]
defender: Get:108 https://deb.debian.org/debian bookworm/main amd64 libnuma-dev amd64 2.0.16-1 [35.0 kB]
defender: Get:109 https://deb.debian.org/debian bookworm/main amd64 libltdl7 amd64 2.4.7-7~deb12u1 [393 kB]
defender: Get:110 https://deb.debian.org/debian bookworm/main amd64 libltdl-dev amd64 2.4.7-7~deb12u1 [164 kB]
defender: Get:111 https://deb.debian.org/debian bookworm/main amd64 libhwloc-dev amd64 2.9.0-1 [241 kB]
defender: Get:112 https://deb.debian.org/debian bookworm/main amd64 libevent-2.1-7 amd64 2.1.12-stable-8 [180 kB]
defender: Get:113 https://deb.debian.org/debian bookworm/main amd64 libevent-extra-2.1-7 amd64 2.1.12-stable-8 [107 kB]
defender: Get:114 https://deb.debian.org/debian bookworm/main amd64 libevent-openssl-2.1-7 amd64 2.1.12-stable-8 [60.6 kB]
defender: Get:115 https://deb.debian.org/debian bookworm/main amd64 libevent-dev amd64 2.1.12-stable-8 [305 kB]
defender: Get:116 https://deb.debian.org/debian bookworm/main amd64 libpmix-dev amd64 4.2.2-1+deb12u1 [902 kB]
defender: Get:117 https://deb.debian.org/debian bookworm/main amd64 libjs-jquery all 3.6.1+dfsg+~3.5.14-1 [326 kB]
defender: Get:118 https://deb.debian.org/debian bookworm/main amd64 libjs-jquery-ui all 1.13.2+dfsg-1 [250 kB]
defender: Get:119 https://deb.debian.org/debian bookworm/main amd64 openmpi-bin amd64 4.1.4-3+b1 [226 kB]
defender: Get:120 https://deb.debian.org/debian bookworm/main amd64 libopenmpi-dev amd64 4.1.4-3+b1 [970 kB]
defender: Get:121 https://deb.debian.org/debian bookworm/main amd64 mpi-default-dev amd64 1.14 [5548 B]
defender: Get:122 https://deb.debian.org/debian bookworm/main amd64 libboost-mpi1.74-dev amd64 1.74.0+ds1-21 [277 kB]
defender: Get:123 https://deb.debian.org/debian bookworm/main amd64 libboost-mpi-dev amd64 1.74.0.3 [4420 B]
defender: Get:124 https://deb.debian.org/debian bookworm/main amd64 libboost-python1.74.0 amd64 1.74.0+ds1-21 [289 kB]
defender: Get:125 https://deb.debian.org/debian bookworm/main amd64 mpi-default-bin amd64 1.14 [4752 B]
defender: Get:126 https://deb.debian.org/debian bookworm/main amd64 libboost-mpi-python1.74.0 amd64 1.74.0+ds1-21 [341 kB]
defender: Get:127 https://deb.debian.org/debian bookworm/main amd64 libboost-mpi-python1.74-dev amd64 1.74.0+ds1-21 [224 kB]
defender: Get:128 https://deb.debian.org/debian bookworm/main amd64 libboost-mpi-python-dev amd64 1.74.0.3 [4456 B]
defender: Get:129 https://deb.debian.org/debian bookworm/main amd64 libboost-numpy1.74.0 amd64 1.74.0+ds1-21 [229 kB]
defender: Get:130 https://deb.debian.org/debian bookworm/main amd64 libboost-numpy1.74-dev amd64 1.74.0+ds1-21 [232 kB]
defender: Get:131 https://deb.debian.org/debian bookworm/main amd64 libboost-numpy-dev amd64 1.74.0.3 [4376 B]
defender: Get:132 https://deb.debian.org/debian bookworm/main amd64 libboost-program-options1.74.0 amd64 1.74.0+ds1-21 [329 kB]
defender: Get:133 https://deb.debian.org/debian bookworm/main amd64 libboost-program-options1.74-dev amd64 1.74.0+ds1-21 [357 kB]
defender: Get:134 https://deb.debian.org/debian bookworm/main amd64 libboost-program-options-dev amd64 1.74.0.3 [4340 B]
defender: Get:135 https://deb.debian.org/debian bookworm/main amd64 libpython3.11 amd64 3.11.2-6+deb12u6 [1987 kB]
defender: Get:136 https://deb.debian.org/debian bookworm/main amd64 libexpat1-dev amd64 2.5.0-1+deb12u2 [151 kB]
defender: Get:137 https://deb.debian.org/debian bookworm/main amd64 libpython3.11-dev amd64 3.11.2-6+deb12u6 [4742 kB]
defender: Get:138 https://deb.debian.org/debian bookworm/main amd64 libpython3-dev amd64 3.11.2-1+b1 [9572 B]
defender: Get:139 https://deb.debian.org/debian bookworm/main amd64 python3.11-dev amd64 3.11.2-6+deb12u6 [615 kB]
defender: Get:140 https://deb.debian.org/debian bookworm/main amd64 python3-lib2to3 all 3.11.2-3 [76.3 kB]
defender: Get:141 https://deb.debian.org/debian bookworm/main amd64 python3-distutils all 3.11.2-3 [131 kB]
defender: Get:142 https://deb.debian.org/debian bookworm/main amd64 libjs-underscore all 1.13.4~dfsg+~1.11.4-3 [116 kB]
defender: Get:143 https://deb.debian.org/debian bookworm/main amd64 libjs-sphinxdoc all 5.3.0-4 [130 kB]
defender: Get:144 https://deb.debian.org/debian bookworm/main amd64 python3-dev amd64 3.11.2-1+b1 [26.2 kB]
defender: Get:145 https://deb.debian.org/debian bookworm/main amd64 libboost-python1.74-dev amd64 1.74.0+ds1-21 [310 kB]
defender: Get:146 https://deb.debian.org/debian bookworm/main amd64 libboost-python-dev amd64 1.74.0.3 [4632 B]
defender: Get:147 https://deb.debian.org/debian bookworm/main amd64 libboost-random1.74.0 amd64 1.74.0+ds1-21 [226 kB]
defender: Get:148 https://deb.debian.org/debian bookworm/main amd64 libboost-random1.74-dev amd64 1.74.0+ds1-21 [229 kB]
defender: Get:149 https://deb.debian.org/debian bookworm/main amd64 libboost-random-dev amd64 1.74.0.3 [4336 B]
defender: Get:150 https://deb.debian.org/debian bookworm/main amd64 libboost-regex-dev amd64 1.74.0.3 [4600 B]
defender: Get:151 https://deb.debian.org/debian bookworm/main amd64 libboost-serialization-dev amd64 1.74.0.3 [4560 B]
defender: Get:152 https://deb.debian.org/debian bookworm/main amd64 libboost-stacktrace1.74.0 amd64 1.74.0+ds1-21 [260 kB]
defender: Get:153 https://deb.debian.org/debian bookworm/main amd64 libboost-stacktrace1.74-dev amd64 1.74.0+ds1-21 [232 kB]
defender: Get:154 https://deb.debian.org/debian bookworm/main amd64 libboost-stacktrace-dev amd64 1.74.0.3 [4328 B]
defender: Get:155 https://deb.debian.org/debian bookworm/main amd64 libboost-system-dev amd64 1.74.0.3 [4468 B]
defender: Get:156 https://deb.debian.org/debian bookworm/main amd64 libboost-test-dev amd64 1.74.0.3 [4368 B]
defender: Get:157 https://deb.debian.org/debian bookworm/main amd64 libboost-thread-dev amd64 1.74.0.3 [4356 B]
defender: Get:158 https://deb.debian.org/debian bookworm/main amd64 libboost-timer1.74.0 amd64 1.74.0+ds1-21 [226 kB]
defender: Get:159 https://deb.debian.org/debian bookworm/main amd64 libboost-timer1.74-dev amd64 1.74.0+ds1-21 [229 kB]
defender: Get:160 https://deb.debian.org/debian bookworm/main amd64 libboost-timer-dev amd64 1.74.0.3 [4456 B]
defender: Get:161 https://deb.debian.org/debian bookworm/main amd64 libboost-type-erasure1.74.0 amd64 1.74.0+ds1-21 [233 kB]
defender: Get:162 https://deb.debian.org/debian bookworm/main amd64 libboost-type-erasure1.74-dev amd64 1.74.0+ds1-21 [236 kB]
defender: Get:163 https://deb.debian.org/debian bookworm/main amd64 libboost-type-erasure-dev amd64 1.74.0.3 [4428 B]
defender: Get:164 https://deb.debian.org/debian bookworm/main amd64 libboost-wave1.74.0 amd64 1.74.0+ds1-21 [418 kB]
defender: Get:165 https://deb.debian.org/debian bookworm/main amd64 libboost-wave1.74-dev amd64 1.74.0+ds1-21 [473 kB]
defender: Get:166 https://deb.debian.org/debian bookworm/main amd64 libboost-wave-dev amd64 1.74.0.3 [4360 B]
defender: Get:167 https://deb.debian.org/debian bookworm/main amd64 libboost-nowide1.74.0 amd64 1.74.0+ds1-21 [219 kB]
defender: Get:168 https://deb.debian.org/debian bookworm/main amd64 libboost-nowide1.74-dev amd64 1.74.0+ds1-21 [220 kB]
defender: Get:169 https://deb.debian.org/debian bookworm/main amd64 libboost-nowide-dev amd64 1.74.0.3 [4392 B]
defender: Get:170 https://deb.debian.org/debian bookworm/main amd64 libboost-all-dev amd64 1.74.0.3 [4680 B]
defender: Get:171 https://deb.debian.org/debian bookworm/main amd64 libbrotli-dev amd64 1.0.9-2+b6 [287 kB]
defender: Get:172 https://deb.debian.org/debian bookworm/main amd64 libc-ares2 amd64 1.18.1-3 [102 kB]
defender: Get:173 https://deb.debian.org/debian bookworm/main amd64 libc-ares-dev amd64 1.18.1-3 [192 kB]
defender: Get:174 https://deb.debian.org/debian bookworm/main amd64 libcaf-openmpi-3 amd64 2.10.1-1+b1 [37.1 kB]
defender: Get:175 https://deb.debian.org/debian bookworm/main amd64 libcoarrays-dev amd64 2.10.1-1+b1 [37.2 kB]
defender: Get:176 https://deb.debian.org/debian bookworm/main amd64 libcoarrays-openmpi-dev amd64 2.10.1-1+b1 [463 kB]
defender: Get:177 https://deb.debian.org/debian bookworm/main amd64 libcpprest2.10 amd64 2.10.18-1+b1 [778 kB]
defender: Get:178 https://deb.debian.org/debian bookworm/main amd64 libwebsocketpp-dev amd64 0.8.2-4 [128 kB]
defender: Get:179 https://deb.debian.org/debian bookworm/main amd64 libcpprest-dev amd64 2.10.18-1+b1 [167 kB]
defender: Get:180 https://deb.debian.org/debian bookworm/main amd64 libre2-9 amd64 20220601+dfsg-1+b1 [179 kB]
defender: Get:181 https://deb.debian.org/debian bookworm/main amd64 libgrpc29 amd64 1.51.1-3+b1 [2735 kB]
defender: Get:182 https://deb.debian.org/debian bookworm/main amd64 libgrpc++1.51 amd64 1.51.1-3+b1 [475 kB]
defender: Get:183 https://deb.debian.org/debian bookworm/main amd64 libre2-dev amd64 20220601+dfsg-1+b1 [241 kB]
defender: Get:184 https://deb.debian.org/debian bookworm/main amd64 libgrpc-dev amd64 1.51.1-3+b1 [4591 kB]
defender: Get:185 https://deb.debian.org/debian bookworm/main amd64 libgrpc++-dev amd64 1.51.1-3+b1 [618 kB]
defender: Get:186 https://deb.debian.org/debian bookworm/main amd64 libgtest-dev amd64 1.12.1-0.2 [240 kB]
defender: Get:187 https://deb.debian.org/debian bookworm/main amd64 libtool all 2.4.7-7~deb12u1 [517 kB]
defender: Get:188 https://deb.debian.org/debian bookworm/main amd64 protobuf-compiler-grpc amd64 1.51.1-3+b1 [37.8 kB]
defender: apt-listchanges: Reading changelogs...
defender: Fetched 99.6 MB in 57s (1738 kB/s)
(Reading database ... 64312 files and directories currently installed.)
defender: Preparing to unpack .../000-libssl3_3.0.19-1~deb12u2_amd64.deb ...
defender: Unpacking libssl3:amd64 (3.0.19-1~deb12u2) over (3.0.14-1~deb12u1) ...
defender: Preparing to unpack .../001-python3.11_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking python3.11 (3.11.2-6+deb12u6) over (3.11.2-6+deb12u2) ...
defender: Preparing to unpack .../002-libpython3.11-stdlib_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking libpython3.11-stdlib:amd64 (3.11.2-6+deb12u6) over (3.11.2-6+deb12u2) ...
defender: Preparing to unpack .../003-python3.11-minimal_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking python3.11-minimal (3.11.2-6+deb12u6) over (3.11.2-6+deb12u2) ...
defender: Preparing to unpack .../004-libpython3.11-minimal_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking libpython3.11-minimal:amd64 (3.11.2-6+deb12u6) over (3.11.2-6+deb12u2) ...
defender: Preparing to unpack .../005-libexpat1_2.5.0-1+deb12u2_amd64.deb ...
defender: Unpacking libexpat1:amd64 (2.5.0-1+deb12u2) over (2.5.0-1) ...
defender: Selecting previously unselected package m4.
defender: Preparing to unpack .../006-m4_1.4.19-3_amd64.deb ...
defender: Unpacking m4 (1.4.19-3) ...
defender: Selecting previously unselected package autoconf.
defender: Preparing to unpack .../007-autoconf_2.71-3_all.deb ...
defender: Unpacking autoconf (2.71-3) ...
defender: Selecting previously unselected package autotools-dev.
defender: Preparing to unpack .../008-autotools-dev_20220109.1_all.deb ...
defender: Unpacking autotools-dev (20220109.1) ...
defender: Selecting previously unselected package automake.
defender: Preparing to unpack .../009-automake_1%3a1.16.5-1.3_all.deb ...
defender: Unpacking automake (1:1.16.5-1.3) ...
defender: Selecting previously unselected package libarchive13:amd64.
defender: Preparing to unpack .../010-libarchive13_3.6.2-1+deb12u3_amd64.deb ...
defender: Unpacking libarchive13:amd64 (3.6.2-1+deb12u3) ...
defender: Selecting previously unselected package librhash0:amd64.
defender: Preparing to unpack .../011-librhash0_1.4.3-3_amd64.deb ...
defender: Unpacking librhash0:amd64 (1.4.3-3) ...
defender: Selecting previously unselected package cmake-data.
defender: Preparing to unpack .../012-cmake-data_3.25.1-1_all.deb ...
defender: Unpacking cmake-data (3.25.1-1) ...
defender: Selecting previously unselected package cmake.
defender: Preparing to unpack .../013-cmake_3.25.1-1_amd64.deb ...
defender: Unpacking cmake (3.25.1-1) ...
defender: Selecting previously unselected package libgfortran5:amd64.
defender: Preparing to unpack .../014-libgfortran5_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libgfortran5:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package libgfortran-12-dev:amd64.
defender: Preparing to unpack .../015-libgfortran-12-dev_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking libgfortran-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package gfortran-12.
defender: Preparing to unpack .../016-gfortran-12_12.2.0-14+deb12u1_amd64.deb ...
defender: Unpacking gfortran-12 (12.2.0-14+deb12u1) ...
defender: Selecting previously unselected package gfortran.
defender: Preparing to unpack .../017-gfortran_4%3a12.2.0-3_amd64.deb ...
defender: Unpacking gfortran (4:12.2.0-3) ...
defender: Selecting previously unselected package googletest.
defender: Preparing to unpack .../018-googletest_1.12.1-0.2_all.deb ...
defender: Unpacking googletest (1.12.1-0.2) ...
defender: Selecting previously unselected package libnl-3-200:amd64.
defender: Preparing to unpack .../019-libnl-3-200_3.7.0-0.2+b1_amd64.deb ...
defender: Unpacking libnl-3-200:amd64 (3.7.0-0.2+b1) ...
defender: Selecting previously unselected package libnl-route-3-200:amd64.
defender: Preparing to unpack .../020-libnl-route-3-200_3.7.0-0.2+b1_amd64.deb ...
defender: Unpacking libnl-route-3-200:amd64 (3.7.0-0.2+b1) ...
defender: Selecting previously unselected package libibverbs1:amd64.
defender: Preparing to unpack .../021-libibverbs1_44.0-2_amd64.deb ...
defender: Unpacking libibverbs1:amd64 (44.0-2) ...
defender: Selecting previously unselected package ibverbs-providers:amd64.
defender: Preparing to unpack .../022-ibverbs-providers_44.0-2_amd64.deb ...
defender: Unpacking ibverbs-providers:amd64 (44.0-2) ...
defender: Selecting previously unselected package javascript-common.
defender: Preparing to unpack .../023-javascript-common_11+nmu1_all.deb ...
defender: Unpacking javascript-common (11+nmu1) ...
defender: Selecting previously unselected package libabsl-dev:amd64.
defender: Preparing to unpack .../024-libabsl-dev_20220623.1-1+deb12u2_amd64.deb ...
defender: Unpacking libabsl-dev:amd64 (20220623.1-1+deb12u2) ...
defender: Selecting previously unselected package libbenchmark1debian:amd64.
defender: Preparing to unpack .../025-libbenchmark1debian_1.7.1-1_amd64.deb ...
defender: Unpacking libbenchmark1debian:amd64 (1.7.1-1) ...
defender: Selecting previously unselected package libbenchmark-dev:amd64.
defender: Preparing to unpack .../026-libbenchmark-dev_1.7.1-1_amd64.deb ...
defender: Unpacking libbenchmark-dev:amd64 (1.7.1-1) ...
defender: Selecting previously unselected package libboost1.74-dev:amd64.
defender: Preparing to unpack .../027-libboost1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-dev:amd64.
defender: Preparing to unpack .../028-libboost-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost1.74-tools-dev.
defender: Preparing to unpack .../029-libboost1.74-tools-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost1.74-tools-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-tools-dev.
defender: Preparing to unpack .../030-libboost-tools-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-tools-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-atomic1.74.0:amd64.
defender: Preparing to unpack .../031-libboost-atomic1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-atomic1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-atomic1.74-dev:amd64.
defender: Preparing to unpack .../032-libboost-atomic1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-atomic1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-atomic-dev:amd64.
defender: Preparing to unpack .../033-libboost-atomic-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-atomic-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-chrono1.74.0:amd64.
defender: Preparing to unpack .../034-libboost-chrono1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-chrono1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-chrono1.74-dev:amd64.
defender: Preparing to unpack .../035-libboost-chrono1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-chrono1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-chrono-dev:amd64.
defender: Preparing to unpack .../036-libboost-chrono-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-chrono-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-container1.74.0:amd64.
defender: Preparing to unpack .../037-libboost-container1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-container1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-container1.74-dev:amd64.
defender: Preparing to unpack .../038-libboost-container1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-container1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-container-dev:amd64.
defender: Preparing to unpack .../039-libboost-container-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-container-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-date-time1.74.0:amd64.
defender: Preparing to unpack .../040-libboost-date-time1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-date-time1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-serialization1.74.0:amd64.
defender: Preparing to unpack .../041-libboost-serialization1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-serialization1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-serialization1.74-dev:amd64.
defender: Preparing to unpack .../042-libboost-serialization1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-serialization1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-date-time1.74-dev:amd64.
defender: Preparing to unpack .../043-libboost-date-time1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-date-time1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-system1.74.0:amd64.
defender: Preparing to unpack .../044-libboost-system1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-system1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-system1.74-dev:amd64.
defender: Preparing to unpack .../045-libboost-system1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-system1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-thread1.74.0:amd64.
defender: Preparing to unpack .../046-libboost-thread1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-thread1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-thread1.74-dev:amd64.
defender: Preparing to unpack .../047-libboost-thread1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-thread1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-context1.74.0:amd64.
defender: Preparing to unpack .../048-libboost-context1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-context1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-context1.74-dev:amd64.
defender: Preparing to unpack .../049-libboost-context1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-context1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-context-dev:amd64.
defender: Preparing to unpack .../050-libboost-context-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-context-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-coroutine1.74.0:amd64.
defender: Preparing to unpack .../051-libboost-coroutine1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-coroutine1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-coroutine1.74-dev:amd64.
defender: Preparing to unpack .../052-libboost-coroutine1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-coroutine1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-coroutine-dev:amd64.
defender: Preparing to unpack .../053-libboost-coroutine-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-coroutine-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-date-time-dev:amd64.
defender: Preparing to unpack .../054-libboost-date-time-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-date-time-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-exception1.74-dev:amd64.
defender: Preparing to unpack .../055-libboost-exception1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-exception1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-exception-dev:amd64.
defender: Preparing to unpack .../056-libboost-exception-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-exception-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-filesystem1.74.0:amd64.
defender: Preparing to unpack .../057-libboost-filesystem1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-filesystem1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-filesystem1.74-dev:amd64.
defender: Preparing to unpack .../058-libboost-filesystem1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-filesystem1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-fiber1.74.0:amd64.
defender: Preparing to unpack .../059-libboost-fiber1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-fiber1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-fiber1.74-dev:amd64.
defender: Preparing to unpack .../060-libboost-fiber1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-fiber1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-fiber-dev:amd64.
defender: Preparing to unpack .../061-libboost-fiber-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-fiber-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-filesystem-dev:amd64.
defender: Preparing to unpack .../062-libboost-filesystem-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-filesystem-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-regex1.74.0:amd64.
defender: Preparing to unpack .../063-libboost-regex1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-regex1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-graph1.74.0:amd64.
defender: Preparing to unpack .../064-libboost-graph1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-graph1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-regex1.74-dev:amd64.
defender: Preparing to unpack .../065-libboost-regex1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-regex1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-test1.74.0:amd64.
defender: Preparing to unpack .../066-libboost-test1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-test1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-test1.74-dev:amd64.
defender: Preparing to unpack .../067-libboost-test1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-test1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-graph1.74-dev:amd64.
defender: Preparing to unpack .../068-libboost-graph1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-graph1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-graph-dev:amd64.
defender: Preparing to unpack .../069-libboost-graph-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-graph-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libevent-pthreads-2.1-7:amd64.
defender: Preparing to unpack .../070-libevent-pthreads-2.1-7_2.1.12-stable-8_amd64.deb ...
defender: Unpacking libevent-pthreads-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Selecting previously unselected package libpsm-infinipath1.
defender: Preparing to unpack .../071-libpsm-infinipath1_3.3+20.604758e7-6.2_amd64.deb ...
defender: Unpacking libpsm-infinipath1 (3.3+20.604758e7-6.2) ...
defender: Selecting previously unselected package libpsm2-2.
defender: Preparing to unpack .../072-libpsm2-2_11.2.185-2_amd64.deb ...
defender: Unpacking libpsm2-2 (11.2.185-2) ...
defender: Selecting previously unselected package librdmacm1:amd64.
defender: Preparing to unpack .../073-librdmacm1_44.0-2_amd64.deb ...
defender: Unpacking librdmacm1:amd64 (44.0-2) ...
defender: Selecting previously unselected package libfabric1:amd64.
defender: Preparing to unpack .../074-libfabric1_1.17.0-3_amd64.deb ...
defender: Unpacking libfabric1:amd64 (1.17.0-3) ...
defender: Selecting previously unselected package libhwloc15:amd64.
defender: Preparing to unpack .../075-libhwloc15_2.9.0-1_amd64.deb ...
defender: Unpacking libhwloc15:amd64 (2.9.0-1) ...
defender: Selecting previously unselected package libmunge2.
defender: Preparing to unpack .../076-libmunge2_0.5.15-2+deb12u1_amd64.deb ...
defender: Unpacking libmunge2 (0.5.15-2+deb12u1) ...
defender: Selecting previously unselected package libpciaccess0:amd64.
defender: Preparing to unpack .../077-libpciaccess0_0.17-2_amd64.deb ...
defender: Unpacking libpciaccess0:amd64 (0.17-2) ...
defender: Selecting previously unselected package libxext6:amd64.
defender: Preparing to unpack .../078-libxext6_2%3a1.3.4-1+b1_amd64.deb ...
defender: Unpacking libxext6:amd64 (2:1.3.4-1+b1) ...
defender: Selecting previously unselected package libxnvctrl0:amd64.
defender: Preparing to unpack .../079-libxnvctrl0_525.85.05-3~deb12u1_amd64.deb ...
defender: Unpacking libxnvctrl0:amd64 (525.85.05-3~deb12u1) ...
defender: Selecting previously unselected package ocl-icd-libopencl1:amd64.
defender: Preparing to unpack .../080-ocl-icd-libopencl1_2.3.1-1_amd64.deb ...
defender: Unpacking ocl-icd-libopencl1:amd64 (2.3.1-1) ...
defender: Selecting previously unselected package libhwloc-plugins:amd64.
defender: Preparing to unpack .../081-libhwloc-plugins_2.9.0-1_amd64.deb ...
defender: Unpacking libhwloc-plugins:amd64 (2.9.0-1) ...
defender: Selecting previously unselected package libpmix2:amd64.
defender: Preparing to unpack .../082-libpmix2_4.2.2-1+deb12u1_amd64.deb ...
defender: Unpacking libpmix2:amd64 (4.2.2-1+deb12u1) ...
defender: Selecting previously unselected package libucx0:amd64.
defender: Preparing to unpack .../083-libucx0_1.13.1-1_amd64.deb ...
defender: Unpacking libucx0:amd64 (1.13.1-1) ...
defender: Selecting previously unselected package libopenmpi3:amd64.
defender: Preparing to unpack .../084-libopenmpi3_4.1.4-3+b1_amd64.deb ...
defender: Unpacking libopenmpi3:amd64 (4.1.4-3+b1) ...
defender: Selecting previously unselected package libboost-mpi1.74.0.
defender: Preparing to unpack .../085-libboost-mpi1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-mpi1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-graph-parallel1.74.0.
defender: Preparing to unpack .../086-libboost-graph-parallel1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-graph-parallel1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-graph-parallel1.74-dev.
defender: Preparing to unpack .../087-libboost-graph-parallel1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-graph-parallel1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-graph-parallel-dev.
defender: Preparing to unpack .../088-libboost-graph-parallel-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-graph-parallel-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-iostreams1.74.0:amd64.
defender: Preparing to unpack .../089-libboost-iostreams1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-iostreams1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-iostreams1.74-dev:amd64.
defender: Preparing to unpack .../090-libboost-iostreams1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-iostreams1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-iostreams-dev:amd64.
defender: Preparing to unpack .../091-libboost-iostreams-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-iostreams-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-locale1.74.0:amd64.
defender: Preparing to unpack .../092-libboost-locale1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-locale1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-locale1.74-dev:amd64.
defender: Preparing to unpack .../093-libboost-locale1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-locale1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-locale-dev:amd64.
defender: Preparing to unpack .../094-libboost-locale-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-locale-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-log1.74.0.
defender: Preparing to unpack .../095-libboost-log1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-log1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-log1.74-dev.
defender: Preparing to unpack .../096-libboost-log1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-log1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-log-dev.
defender: Preparing to unpack .../097-libboost-log-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-log-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-math1.74.0:amd64.
defender: Preparing to unpack .../098-libboost-math1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-math1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-math1.74-dev:amd64.
defender: Preparing to unpack .../099-libboost-math1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-math1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-math-dev:amd64.
defender: Preparing to unpack .../100-libboost-math-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-math-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package openmpi-common.
defender: Preparing to unpack .../101-openmpi-common_4.1.4-3_all.deb ...
defender: Unpacking openmpi-common (4.1.4-3) ...
defender: Selecting previously unselected package libnl-3-dev:amd64.
defender: Preparing to unpack .../102-libnl-3-dev_3.7.0-0.2+b1_amd64.deb ...
defender: Unpacking libnl-3-dev:amd64 (3.7.0-0.2+b1) ...
defender: Selecting previously unselected package libnl-route-3-dev:amd64.
defender: Preparing to unpack .../103-libnl-route-3-dev_3.7.0-0.2+b1_amd64.deb ...
defender: Unpacking libnl-route-3-dev:amd64 (3.7.0-0.2+b1) ...
defender: Selecting previously unselected package libibverbs-dev:amd64.
defender: Preparing to unpack .../104-libibverbs-dev_44.0-2_amd64.deb ...
defender: Unpacking libibverbs-dev:amd64 (44.0-2) ...
defender: Selecting previously unselected package libnuma-dev:amd64.
defender: Preparing to unpack .../105-libnuma-dev_2.0.16-1_amd64.deb ...
defender: Unpacking libnuma-dev:amd64 (2.0.16-1) ...
defender: Selecting previously unselected package libltdl7:amd64.
defender: Preparing to unpack .../106-libltdl7_2.4.7-7~deb12u1_amd64.deb ...
defender: Unpacking libltdl7:amd64 (2.4.7-7~deb12u1) ...
defender: Selecting previously unselected package libltdl-dev:amd64.
defender: Preparing to unpack .../107-libltdl-dev_2.4.7-7~deb12u1_amd64.deb ...
defender: Unpacking libltdl-dev:amd64 (2.4.7-7~deb12u1) ...
defender: Selecting previously unselected package libhwloc-dev:amd64.
defender: Preparing to unpack .../108-libhwloc-dev_2.9.0-1_amd64.deb ...
defender: Unpacking libhwloc-dev:amd64 (2.9.0-1) ...
defender: Selecting previously unselected package libevent-2.1-7:amd64.
defender: Preparing to unpack .../109-libevent-2.1-7_2.1.12-stable-8_amd64.deb ...
defender: Unpacking libevent-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Selecting previously unselected package libevent-extra-2.1-7:amd64.
defender: Preparing to unpack .../110-libevent-extra-2.1-7_2.1.12-stable-8_amd64.deb ...
defender: Unpacking libevent-extra-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Selecting previously unselected package libevent-openssl-2.1-7:amd64.
defender: Preparing to unpack .../111-libevent-openssl-2.1-7_2.1.12-stable-8_amd64.deb ...
defender: Unpacking libevent-openssl-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Selecting previously unselected package libevent-dev.
defender: Preparing to unpack .../112-libevent-dev_2.1.12-stable-8_amd64.deb ...
defender: Unpacking libevent-dev (2.1.12-stable-8) ...
defender: Selecting previously unselected package libpmix-dev:amd64.
defender: Preparing to unpack .../113-libpmix-dev_4.2.2-1+deb12u1_amd64.deb ...
defender: Unpacking libpmix-dev:amd64 (4.2.2-1+deb12u1) ...
defender: Selecting previously unselected package libjs-jquery.
defender: Preparing to unpack .../114-libjs-jquery_3.6.1+dfsg+~3.5.14-1_all.deb ...
defender: Unpacking libjs-jquery (3.6.1+dfsg+~3.5.14-1) ...
defender: Selecting previously unselected package libjs-jquery-ui.
defender: Preparing to unpack .../115-libjs-jquery-ui_1.13.2+dfsg-1_all.deb ...
defender: Unpacking libjs-jquery-ui (1.13.2+dfsg-1) ...
defender: Selecting previously unselected package openmpi-bin.
defender: Preparing to unpack .../116-openmpi-bin_4.1.4-3+b1_amd64.deb ...
defender: Unpacking openmpi-bin (4.1.4-3+b1) ...
defender: Selecting previously unselected package libopenmpi-dev:amd64.
defender: Preparing to unpack .../117-libopenmpi-dev_4.1.4-3+b1_amd64.deb ...
defender: Unpacking libopenmpi-dev:amd64 (4.1.4-3+b1) ...
defender: Selecting previously unselected package mpi-default-dev.
defender: Preparing to unpack .../118-mpi-default-dev_1.14_amd64.deb ...
defender: Unpacking mpi-default-dev (1.14) ...
defender: Selecting previously unselected package libboost-mpi1.74-dev.
defender: Preparing to unpack .../119-libboost-mpi1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-mpi1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-mpi-dev.
defender: Preparing to unpack .../120-libboost-mpi-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-mpi-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-python1.74.0.
defender: Preparing to unpack .../121-libboost-python1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-python1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package mpi-default-bin.
defender: Preparing to unpack .../122-mpi-default-bin_1.14_amd64.deb ...
defender: Unpacking mpi-default-bin (1.14) ...
defender: Selecting previously unselected package libboost-mpi-python1.74.0.
defender: Preparing to unpack .../123-libboost-mpi-python1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-mpi-python1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-mpi-python1.74-dev.
defender: Preparing to unpack .../124-libboost-mpi-python1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-mpi-python1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-mpi-python-dev.
defender: Preparing to unpack .../125-libboost-mpi-python-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-mpi-python-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-numpy1.74.0.
defender: Preparing to unpack .../126-libboost-numpy1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-numpy1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-numpy1.74-dev.
defender: Preparing to unpack .../127-libboost-numpy1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-numpy1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-numpy-dev.
defender: Preparing to unpack .../128-libboost-numpy-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-numpy-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-program-options1.74.0:amd64.
defender: Preparing to unpack .../129-libboost-program-options1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-program-options1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-program-options1.74-dev:amd64.
defender: Preparing to unpack .../130-libboost-program-options1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-program-options1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-program-options-dev:amd64.
defender: Preparing to unpack .../131-libboost-program-options-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-program-options-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libpython3.11:amd64.
defender: Preparing to unpack .../132-libpython3.11_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking libpython3.11:amd64 (3.11.2-6+deb12u6) ...
defender: Selecting previously unselected package libexpat1-dev:amd64.
defender: Preparing to unpack .../133-libexpat1-dev_2.5.0-1+deb12u2_amd64.deb ...
defender: Unpacking libexpat1-dev:amd64 (2.5.0-1+deb12u2) ...
defender: Selecting previously unselected package libpython3.11-dev:amd64.
defender: Preparing to unpack .../134-libpython3.11-dev_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking libpython3.11-dev:amd64 (3.11.2-6+deb12u6) ...
defender: Selecting previously unselected package libpython3-dev:amd64.
defender: Preparing to unpack .../135-libpython3-dev_3.11.2-1+b1_amd64.deb ...
defender: Unpacking libpython3-dev:amd64 (3.11.2-1+b1) ...
defender: Selecting previously unselected package python3.11-dev.
defender: Preparing to unpack .../136-python3.11-dev_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking python3.11-dev (3.11.2-6+deb12u6) ...
defender: Selecting previously unselected package python3-lib2to3.
defender: Preparing to unpack .../137-python3-lib2to3_3.11.2-3_all.deb ...
defender: Unpacking python3-lib2to3 (3.11.2-3) ...
defender: Selecting previously unselected package python3-distutils.
defender: Preparing to unpack .../138-python3-distutils_3.11.2-3_all.deb ...
defender: Unpacking python3-distutils (3.11.2-3) ...
defender: Selecting previously unselected package libjs-underscore.
defender: Preparing to unpack .../139-libjs-underscore_1.13.4~dfsg+~1.11.4-3_all.deb ...
defender: Unpacking libjs-underscore (1.13.4~dfsg+~1.11.4-3) ...
defender: Selecting previously unselected package libjs-sphinxdoc.
defender: Preparing to unpack .../140-libjs-sphinxdoc_5.3.0-4_all.deb ...
defender: Unpacking libjs-sphinxdoc (5.3.0-4) ...
defender: Selecting previously unselected package python3-dev.
defender: Preparing to unpack .../141-python3-dev_3.11.2-1+b1_amd64.deb ...
defender: Unpacking python3-dev (3.11.2-1+b1) ...
defender: Selecting previously unselected package libboost-python1.74-dev.
defender: Preparing to unpack .../142-libboost-python1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-python1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-python-dev.
defender: Preparing to unpack .../143-libboost-python-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-python-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-random1.74.0:amd64.
defender: Preparing to unpack .../144-libboost-random1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-random1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-random1.74-dev:amd64.
defender: Preparing to unpack .../145-libboost-random1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-random1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-random-dev:amd64.
defender: Preparing to unpack .../146-libboost-random-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-random-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-regex-dev:amd64.
defender: Preparing to unpack .../147-libboost-regex-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-regex-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-serialization-dev:amd64.
defender: Preparing to unpack .../148-libboost-serialization-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-serialization-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-stacktrace1.74.0:amd64.
defender: Preparing to unpack .../149-libboost-stacktrace1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-stacktrace1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-stacktrace1.74-dev:amd64.
defender: Preparing to unpack .../150-libboost-stacktrace1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-stacktrace1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-stacktrace-dev:amd64.
defender: Preparing to unpack .../151-libboost-stacktrace-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-stacktrace-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-system-dev:amd64.
defender: Preparing to unpack .../152-libboost-system-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-system-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-test-dev:amd64.
defender: Preparing to unpack .../153-libboost-test-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-test-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-thread-dev:amd64.
defender: Preparing to unpack .../154-libboost-thread-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-thread-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-timer1.74.0:amd64.
defender: Preparing to unpack .../155-libboost-timer1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-timer1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-timer1.74-dev:amd64.
defender: Preparing to unpack .../156-libboost-timer1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-timer1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-timer-dev:amd64.
defender: Preparing to unpack .../157-libboost-timer-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-timer-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-type-erasure1.74.0:amd64.
defender: Preparing to unpack .../158-libboost-type-erasure1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-type-erasure1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-type-erasure1.74-dev:amd64.
defender: Preparing to unpack .../159-libboost-type-erasure1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-type-erasure1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-type-erasure-dev:amd64.
defender: Preparing to unpack .../160-libboost-type-erasure-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-type-erasure-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-wave1.74.0:amd64.
defender: Preparing to unpack .../161-libboost-wave1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-wave1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-wave1.74-dev:amd64.
defender: Preparing to unpack .../162-libboost-wave1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-wave1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-wave-dev:amd64.
defender: Preparing to unpack .../163-libboost-wave-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-wave-dev:amd64 (1.74.0.3) ...
defender: Selecting previously unselected package libboost-nowide1.74.0.
defender: Preparing to unpack .../164-libboost-nowide1.74.0_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-nowide1.74.0 (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-nowide1.74-dev.
defender: Preparing to unpack .../165-libboost-nowide1.74-dev_1.74.0+ds1-21_amd64.deb ...
defender: Unpacking libboost-nowide1.74-dev (1.74.0+ds1-21) ...
defender: Selecting previously unselected package libboost-nowide-dev.
defender: Preparing to unpack .../166-libboost-nowide-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-nowide-dev (1.74.0.3) ...
defender: Selecting previously unselected package libboost-all-dev.
defender: Preparing to unpack .../167-libboost-all-dev_1.74.0.3_amd64.deb ...
defender: Unpacking libboost-all-dev (1.74.0.3) ...
defender: Selecting previously unselected package libbrotli-dev:amd64.
defender: Preparing to unpack .../168-libbrotli-dev_1.0.9-2+b6_amd64.deb ...
defender: Unpacking libbrotli-dev:amd64 (1.0.9-2+b6) ...
defender: Selecting previously unselected package libc-ares2:amd64.
defender: Preparing to unpack .../169-libc-ares2_1.18.1-3_amd64.deb ...
defender: Unpacking libc-ares2:amd64 (1.18.1-3) ...
defender: Selecting previously unselected package libc-ares-dev:amd64.
defender: Preparing to unpack .../170-libc-ares-dev_1.18.1-3_amd64.deb ...
defender: Unpacking libc-ares-dev:amd64 (1.18.1-3) ...
defender: Selecting previously unselected package libcaf-openmpi-3:amd64.
defender: Preparing to unpack .../171-libcaf-openmpi-3_2.10.1-1+b1_amd64.deb ...
defender: Unpacking libcaf-openmpi-3:amd64 (2.10.1-1+b1) ...
defender: Selecting previously unselected package libcoarrays-dev:amd64.
defender: Preparing to unpack .../172-libcoarrays-dev_2.10.1-1+b1_amd64.deb ...
defender: Unpacking libcoarrays-dev:amd64 (2.10.1-1+b1) ...
defender: Selecting previously unselected package libcoarrays-openmpi-dev:amd64.
defender: Preparing to unpack .../173-libcoarrays-openmpi-dev_2.10.1-1+b1_amd64.deb ...
defender: Unpacking libcoarrays-openmpi-dev:amd64 (2.10.1-1+b1) ...
defender: Selecting previously unselected package libcpprest2.10:amd64.
defender: Preparing to unpack .../174-libcpprest2.10_2.10.18-1+b1_amd64.deb ...
defender: Unpacking libcpprest2.10:amd64 (2.10.18-1+b1) ...
defender: Selecting previously unselected package libssl-dev:amd64.
defender: Preparing to unpack .../175-libssl-dev_3.0.19-1~deb12u2_amd64.deb ...
defender: Unpacking libssl-dev:amd64 (3.0.19-1~deb12u2) ...
defender: Selecting previously unselected package libwebsocketpp-dev:amd64.
defender: Preparing to unpack .../176-libwebsocketpp-dev_0.8.2-4_amd64.deb ...
defender: Unpacking libwebsocketpp-dev:amd64 (0.8.2-4) ...
defender: Selecting previously unselected package libcpprest-dev:amd64.
defender: Preparing to unpack .../177-libcpprest-dev_2.10.18-1+b1_amd64.deb ...
defender: Unpacking libcpprest-dev:amd64 (2.10.18-1+b1) ...
defender: Selecting previously unselected package libre2-9:amd64.
defender: Preparing to unpack .../178-libre2-9_20220601+dfsg-1+b1_amd64.deb ...
defender: Unpacking libre2-9:amd64 (20220601+dfsg-1+b1) ...
defender: Selecting previously unselected package libgrpc29:amd64.
defender: Preparing to unpack .../179-libgrpc29_1.51.1-3+b1_amd64.deb ...
defender: Unpacking libgrpc29:amd64 (1.51.1-3+b1) ...
defender: Selecting previously unselected package libgrpc++1.51:amd64.
defender: Preparing to unpack .../180-libgrpc++1.51_1.51.1-3+b1_amd64.deb ...
defender: Unpacking libgrpc++1.51:amd64 (1.51.1-3+b1) ...
defender: Selecting previously unselected package libre2-dev:amd64.
defender: Preparing to unpack .../181-libre2-dev_20220601+dfsg-1+b1_amd64.deb ...
defender: Unpacking libre2-dev:amd64 (20220601+dfsg-1+b1) ...
defender: Selecting previously unselected package libgrpc-dev:amd64.
defender: Preparing to unpack .../182-libgrpc-dev_1.51.1-3+b1_amd64.deb ...
defender: Unpacking libgrpc-dev:amd64 (1.51.1-3+b1) ...
defender: Selecting previously unselected package libgrpc++-dev:amd64.
defender: Preparing to unpack .../183-libgrpc++-dev_1.51.1-3+b1_amd64.deb ...
defender: Unpacking libgrpc++-dev:amd64 (1.51.1-3+b1) ...
defender: Selecting previously unselected package libgtest-dev:amd64.
defender: Preparing to unpack .../184-libgtest-dev_1.12.1-0.2_amd64.deb ...
defender: Unpacking libgtest-dev:amd64 (1.12.1-0.2) ...
defender: Selecting previously unselected package libtool.
defender: Preparing to unpack .../185-libtool_2.4.7-7~deb12u1_all.deb ...
defender: Unpacking libtool (2.4.7-7~deb12u1) ...
defender: Preparing to unpack .../186-openssl_3.0.19-1~deb12u2_amd64.deb ...
defender: Unpacking openssl (3.0.19-1~deb12u2) over (3.0.14-1~deb12u1) ...
defender: Selecting previously unselected package protobuf-compiler-grpc.
defender: Preparing to unpack .../187-protobuf-compiler-grpc_1.51.1-3+b1_amd64.deb ...
defender: Unpacking protobuf-compiler-grpc (1.51.1-3+b1) ...
defender: Setting up libboost-chrono1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libexpat1:amd64 (2.5.0-1+deb12u2) ...
defender: Setting up libboost-system1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up javascript-common (11+nmu1) ...
defender: Setting up libpciaccess0:amd64 (0.17-2) ...
defender: Setting up libre2-9:amd64 (20220601+dfsg-1+b1) ...
defender: Setting up libevent-extra-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Setting up libboost1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-atomic1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libbenchmark1debian:amd64 (1.7.1-1) ...
defender: Setting up libarchive13:amd64 (3.6.2-1+deb12u3) ...
defender: Setting up libboost-iostreams1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-program-options1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-chrono1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libbenchmark-dev:amd64 (1.7.1-1) ...
defender: Setting up libssl3:amd64 (3.0.19-1~deb12u2) ...
defender: Setting up libboost-stacktrace1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libxext6:amd64 (2:1.3.4-1+b1) ...
defender: Setting up libevent-openssl-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Setting up m4 (1.4.19-3) ...
defender: Setting up libboost-nowide1.74.0 (1.74.0+ds1-21) ...
defender: Setting up libboost-filesystem1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-exception1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libc-ares2:amd64 (1.18.1-3) ...
defender: Setting up libboost-exception-dev:amd64 (1.74.0.3) ...
defender: Setting up googletest (1.12.1-0.2) ...
defender: Setting up libboost-program-options1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libnuma-dev:amd64 (2.0.16-1) ...
defender: Setting up libxnvctrl0:amd64 (525.85.05-3~deb12u1) ...
defender: Setting up autotools-dev (20220109.1) ...
defender: Setting up libmunge2 (0.5.15-2+deb12u1) ...
defender: Setting up libexpat1-dev:amd64 (2.5.0-1+deb12u2) ...
defender: Setting up libboost-test1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-program-options-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-system1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-nowide1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libboost-regex1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libssl-dev:amd64 (3.0.19-1~deb12u2) ...
defender: Setting up libhwloc15:amd64 (2.9.0-1) ...
defender: Setting up libc-ares-dev:amd64 (1.18.1-3) ...
defender: Setting up libboost-context1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libevent-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Setting up libboost-graph1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-random1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost1.74-tools-dev (1.74.0+ds1-21) ...
defender: Setting up libabsl-dev:amd64 (20220623.1-1+deb12u2) ...
defender: Setting up libltdl7:amd64 (2.4.7-7~deb12u1) ...
defender: Setting up libgfortran5:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up autoconf (2.71-3) ...
defender: Setting up libboost-atomic1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-math1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libgrpc29:amd64 (1.51.1-3+b1) ...
defender: Setting up libboost-serialization1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-atomic-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-container1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-regex1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up ocl-icd-libopencl1:amd64 (2.3.1-1) ...
defender: Setting up libwebsocketpp-dev:amd64 (0.8.2-4) ...
defender: Setting up librhash0:amd64 (1.4.3-3) ...
defender: Setting up libcpprest2.10:amd64 (2.10.18-1+b1) ...
defender: Setting up libnl-3-200:amd64 (3.7.0-0.2+b1) ...
defender: Setting up libpsm2-2 (11.2.185-2) ...
defender: Setting up openmpi-common (4.1.4-3) ...
defender: Setting up cmake-data (3.25.1-1) ...
defender: Setting up libboost-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-math1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libpython3.11-minimal:amd64 (3.11.2-6+deb12u6) ...
defender: Setting up libpsm-infinipath1 (3.3+20.604758e7-6.2) ...
defender: update-alternatives: using /usr/lib/libpsm1/libpsm_infinipath.so.1.16 to provide /usr/lib/x86_64-linux-gnu/libpsm_infinipath.so.1 (libpsm_infinipath.so.1) in auto mode
defender: Setting up libboost-filesystem1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libjs-jquery (3.6.1+dfsg+~3.5.14-1) ...
defender: Setting up libboost-date-time1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-python1.74.0 (1.74.0+ds1-21) ...
defender: Setting up libboost-fiber1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-stacktrace1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libre2-dev:amd64 (20220601+dfsg-1+b1) ...
defender: Setting up libboost-test1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up openssl (3.0.19-1~deb12u2) ...
defender: Setting up libboost-regex-dev:amd64 (1.74.0.3) ...
defender: Setting up python3-lib2to3 (3.11.2-3) ...
defender: Setting up libboost-timer1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-filesystem-dev:amd64 (1.74.0.3) ...
defender: Setting up libbrotli-dev:amd64 (1.0.9-2+b6) ...
defender: Setting up libjs-underscore (1.13.4~dfsg+~1.11.4-3) ...
defender: Setting up libboost-thread1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-numpy1.74.0 (1.74.0+ds1-21) ...
defender: Setting up libevent-pthreads-2.1-7:amd64 (2.1.12-stable-8) ...
defender: Setting up automake (1:1.16.5-1.3) ...
defender: update-alternatives: using /usr/bin/automake-1.16 to provide /usr/bin/automake (automake) in auto mode
defender: Setting up python3-distutils (3.11.2-3) ...
defender: Setting up python3.11-minimal (3.11.2-6+deb12u6) ...
defender: Setting up libboost-log1.74.0 (1.74.0+ds1-21) ...
defender: Setting up libgtest-dev:amd64 (1.12.1-0.2) ...
defender: Setting up libgrpc++1.51:amd64 (1.51.1-3+b1) ...
defender: Setting up libtool (2.4.7-7~deb12u1) ...
defender: Setting up libboost-container1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-chrono-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-math-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-coroutine1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libpython3.11-stdlib:amd64 (3.11.2-6+deb12u6) ...
defender: Setting up libboost-system-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-tools-dev (1.74.0.3) ...
defender: Setting up libgfortran-12-dev:amd64 (12.2.0-14+deb12u1) ...
defender: Setting up libhwloc-plugins:amd64 (2.9.0-1) ...
defender: Setting up libboost-nowide-dev (1.74.0.3) ...
defender: Setting up libgrpc-dev:amd64 (1.51.1-3+b1) ...
defender: Setting up libboost-container-dev:amd64 (1.74.0.3) ...
defender: Setting up libnl-route-3-200:amd64 (3.7.0-0.2+b1) ...
defender: Setting up libboost-test-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-iostreams1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libltdl-dev:amd64 (2.4.7-7~deb12u1) ...
defender: Setting up gfortran-12 (12.2.0-14+deb12u1) ...
defender: Setting up libjs-jquery-ui (1.13.2+dfsg-1) ...
defender: Setting up protobuf-compiler-grpc (1.51.1-3+b1) ...
defender: Setting up libevent-dev (2.1.12-stable-8) ...
defender: Setting up libboost-random1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-timer1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-numpy1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libjs-sphinxdoc (5.3.0-4) ...
defender: Setting up libboost-serialization1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-wave1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libnl-3-dev:amd64 (3.7.0-0.2+b1) ...
defender: Setting up libboost-stacktrace-dev:amd64 (1.74.0.3) ...
defender: Setting up libgrpc++-dev:amd64 (1.51.1-3+b1) ...
defender: Setting up cmake (3.25.1-1) ...
defender: Setting up libhwloc-dev:amd64 (2.9.0-1) ...
defender: Setting up libboost-locale1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-timer-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-type-erasure1.74.0:amd64 (1.74.0+ds1-21) ...
defender: Setting up python3.11 (3.11.2-6+deb12u6) ...
defender: Setting up libibverbs1:amd64 (44.0-2) ...
defender: Setting up libboost-wave1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libpython3.11:amd64 (3.11.2-6+deb12u6) ...
defender: Setting up libpmix2:amd64 (4.2.2-1+deb12u1) ...
defender: Setting up ibverbs-providers:amd64 (44.0-2) ...
defender: Setting up libboost-random-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-wave-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-iostreams-dev:amd64 (1.74.0.3) ...
defender: Setting up gfortran (4:12.2.0-3) ...
defender: update-alternatives: using /usr/bin/gfortran to provide /usr/bin/f95 (f95) in auto mode
defender: update-alternatives: using /usr/bin/gfortran to provide /usr/bin/f77 (f77) in auto mode
defender: Setting up libnl-route-3-dev:amd64 (3.7.0-0.2+b1) ...
defender: Setting up libboost-date-time1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libpython3.11-dev:amd64 (3.11.2-6+deb12u6) ...
defender: Setting up libboost-graph1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-numpy-dev (1.74.0.3) ...
defender: Setting up libboost-serialization-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-date-time-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-thread1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libpmix-dev:amd64 (4.2.2-1+deb12u1) ...
defender: Setting up libboost-thread-dev:amd64 (1.74.0.3) ...
defender: Setting up librdmacm1:amd64 (44.0-2) ...
defender: Setting up libboost-graph-dev:amd64 (1.74.0.3) ...
defender: Setting up libucx0:amd64 (1.13.1-1) ...
defender: Setting up libpython3-dev:amd64 (3.11.2-1+b1) ...
defender: Setting up libboost-log1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libcoarrays-dev:amd64 (2.10.1-1+b1) ...
defender: Setting up python3.11-dev (3.11.2-6+deb12u6) ...
defender: Setting up libibverbs-dev:amd64 (44.0-2) ...
defender: Setting up libboost-context1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-fiber1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-type-erasure1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up python3-dev (3.11.2-1+b1) ...
defender: Setting up libboost-locale1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libcpprest-dev:amd64 (2.10.18-1+b1) ...
defender: Setting up libboost-coroutine1.74-dev:amd64 (1.74.0+ds1-21) ...
defender: Setting up libboost-coroutine-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-log-dev (1.74.0.3) ...
defender: Setting up libboost-fiber-dev:amd64 (1.74.0.3) ...
defender: Setting up libfabric1:amd64 (1.17.0-3) ...
defender: Setting up libopenmpi3:amd64 (4.1.4-3+b1) ...
defender: Setting up libboost-mpi1.74.0 (1.74.0+ds1-21) ...
defender: Setting up libboost-locale-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-context-dev:amd64 (1.74.0.3) ...
defender: Setting up libboost-python1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libboost-python-dev (1.74.0.3) ...
defender: Setting up libboost-type-erasure-dev:amd64 (1.74.0.3) ...
defender: Setting up libcaf-openmpi-3:amd64 (2.10.1-1+b1) ...
defender: Setting up libboost-graph-parallel1.74.0 (1.74.0+ds1-21) ...
defender: Setting up openmpi-bin (4.1.4-3+b1) ...
defender: update-alternatives: using /usr/bin/mpirun.openmpi to provide /usr/bin/mpirun (mpirun) in auto mode
defender: update-alternatives: using /usr/bin/mpicc.openmpi to provide /usr/bin/mpicc (mpi) in auto mode
defender: Setting up mpi-default-bin (1.14) ...
defender: Setting up libcoarrays-openmpi-dev:amd64 (2.10.1-1+b1) ...
defender: update-alternatives: using /usr/lib/x86_64-linux-gnu/open-coarrays/openmpi/bin/caf to provide /usr/bin/caf.openmpi (caf-openmpi) in auto mode
defender: update-alternatives: using /usr/bin/caf.openmpi to provide /usr/bin/caf (caf) in auto mode
defender: Setting up libboost-graph-parallel1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libopenmpi-dev:amd64 (4.1.4-3+b1) ...
defender: update-alternatives: using /usr/lib/x86_64-linux-gnu/openmpi/include to provide /usr/include/x86_64-linux-gnu/mpi (mpi-x86_64-linux-gnu) in auto mode
defender: Setting up libboost-mpi-python1.74.0 (1.74.0+ds1-21) ...
defender: Setting up libboost-graph-parallel-dev (1.74.0.3) ...
defender: Setting up mpi-default-dev (1.14) ...
defender: Setting up libboost-mpi1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libboost-mpi-python1.74-dev (1.74.0+ds1-21) ...
defender: Setting up libboost-mpi-python-dev (1.74.0.3) ...
defender: Setting up libboost-mpi-dev (1.74.0.3) ...
defender: Setting up libboost-all-dev (1.74.0.3) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: Processing triggers for systemd (252.30-1~deb12u2) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for mailcap (3.70+nmu1) ...
defender: ++ apt-get install -y python3 python3-pip python3-venv python3-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: python3 is already the newest version (3.11.2-1+b1).
defender: python3 set to manually installed.
defender: python3-dev is already the newest version (3.11.2-1+b1).
defender: python3-dev set to manually installed.
defender: The following additional packages will be installed:
defender:   python3-pip-whl python3-pkg-resources python3-setuptools
defender:   python3-setuptools-whl python3-wheel python3.11-venv
defender: Suggested packages:
defender:   python-setuptools-doc
defender: The following NEW packages will be installed:
defender:   python3-pip python3-pip-whl python3-setuptools python3-setuptools-whl
defender:   python3-venv python3-wheel python3.11-venv
defender: The following packages will be upgraded:
defender:   python3-pkg-resources
defender: 1 upgraded, 7 newly installed, 0 to remove and 65 not upgraded.
defender: Need to get 5010 kB of archives.
defender: After this operation, 12.7 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 python3-pkg-resources all 66.1.1-1+deb12u2 [297 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 python3-setuptools all 66.1.1-1+deb12u2 [522 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 python3-wheel all 0.38.4-2 [30.8 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 python3-pip all 23.0.1+dfsg-1 [1325 kB]
defender: Get:5 https://deb.debian.org/debian bookworm/main amd64 python3-pip-whl all 23.0.1+dfsg-1 [1717 kB]
defender: Get:6 https://deb.debian.org/debian bookworm/main amd64 python3-setuptools-whl all 66.1.1-1+deb12u2 [1112 kB]
defender: Get:7 https://deb.debian.org/debian bookworm/main amd64 python3.11-venv amd64 3.11.2-6+deb12u6 [5896 B]
defender: Get:8 https://deb.debian.org/debian bookworm/main amd64 python3-venv amd64 3.11.2-1+b1 [1200 B]
defender: apt-listchanges: Reading changelogs...
defender: Fetched 5010 kB in 3s (1877 kB/s)
(Reading database ... 90252 files and directories currently installed.)
defender: Preparing to unpack .../0-python3-pkg-resources_66.1.1-1+deb12u2_all.deb ...
defender: Unpacking python3-pkg-resources (66.1.1-1+deb12u2) over (66.1.1-1) ...
defender: Selecting previously unselected package python3-setuptools.
defender: Preparing to unpack .../1-python3-setuptools_66.1.1-1+deb12u2_all.deb ...
defender: Unpacking python3-setuptools (66.1.1-1+deb12u2) ...
defender: Selecting previously unselected package python3-wheel.
defender: Preparing to unpack .../2-python3-wheel_0.38.4-2_all.deb ...
defender: Unpacking python3-wheel (0.38.4-2) ...
defender: Selecting previously unselected package python3-pip.
defender: Preparing to unpack .../3-python3-pip_23.0.1+dfsg-1_all.deb ...
defender: Unpacking python3-pip (23.0.1+dfsg-1) ...
defender: Selecting previously unselected package python3-pip-whl.
defender: Preparing to unpack .../4-python3-pip-whl_23.0.1+dfsg-1_all.deb ...
defender: Unpacking python3-pip-whl (23.0.1+dfsg-1) ...
defender: Selecting previously unselected package python3-setuptools-whl.
defender: Preparing to unpack .../5-python3-setuptools-whl_66.1.1-1+deb12u2_all.deb ...
defender: Unpacking python3-setuptools-whl (66.1.1-1+deb12u2) ...
defender: Selecting previously unselected package python3.11-venv.
defender: Preparing to unpack .../6-python3.11-venv_3.11.2-6+deb12u6_amd64.deb ...
defender: Unpacking python3.11-venv (3.11.2-6+deb12u6) ...
defender: Selecting previously unselected package python3-venv.
defender: Preparing to unpack .../7-python3-venv_3.11.2-1+b1_amd64.deb ...
defender: Unpacking python3-venv (3.11.2-1+b1) ...
defender: Setting up python3-pkg-resources (66.1.1-1+deb12u2) ...
defender: Setting up python3-setuptools-whl (66.1.1-1+deb12u2) ...
defender: Setting up python3-setuptools (66.1.1-1+deb12u2) ...
defender: Setting up python3-pip-whl (23.0.1+dfsg-1) ...
defender: Setting up python3-wheel (0.38.4-2) ...
defender: Setting up python3.11-venv (3.11.2-6+deb12u6) ...
defender: Setting up python3-pip (23.0.1+dfsg-1) ...
defender: Setting up python3-venv (3.11.2-1+b1) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: ++ apt-get install -y hping3 nmap tcpreplay netcat-openbsd iperf3 net-tools dnsutils
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   bind9-dnsutils bind9-host bind9-libs libblas3 libdumbnet1 libiperf0
defender:   liblinear4 liblua5.3-0 libpcre3 libsctp1 libtcl8.6 lua-lpeg nmap-common
defender: Suggested packages:
defender:   liblinear-tools liblinear-dev lksctp-tools tcl8.6 ncat ndiff zenmap
defender: The following NEW packages will be installed:
defender:   dnsutils hping3 iperf3 libblas3 libdumbnet1 libiperf0 liblinear4 liblua5.3-0
defender:   libpcre3 libsctp1 libtcl8.6 lua-lpeg net-tools netcat-openbsd nmap
defender:   nmap-common tcpreplay
defender: The following packages will be upgraded:
defender:   bind9-dnsutils bind9-host bind9-libs
defender: 3 upgraded, 17 newly installed, 0 to remove and 62 not upgraded.
defender: Need to get 10.1 MB of archives.
defender: After this operation, 35.8 MB of additional disk space will be used.
defender: Get:1 https://security.debian.org/debian-security bookworm-security/main amd64 bind9-dnsutils amd64 1:9.18.47-1~deb12u1 [156 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libsctp1 amd64 1.0.19+dfsg-2 [29.7 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libiperf0 amd64 3.12-1+deb12u2 [91.2 kB]
defender: Get:4 https://security.debian.org/debian-security bookworm-security/main amd64 bind9-host amd64 1:9.18.47-1~deb12u1 [54.8 kB]
defender: Get:5 https://security.debian.org/debian-security bookworm-security/main amd64 bind9-libs amd64 1:9.18.47-1~deb12u1 [1180 kB]
defender: Get:6 https://deb.debian.org/debian bookworm/main amd64 iperf3 amd64 3.12-1+deb12u2 [34.0 kB]
defender: Get:7 https://deb.debian.org/debian bookworm/main amd64 libtcl8.6 amd64 8.6.13+dfsg-2 [1035 kB]
defender: Get:8 https://deb.debian.org/debian bookworm/main amd64 hping3 amd64 3.a2.ds2-10 [106 kB]
defender: Get:9 https://security.debian.org/debian-security bookworm-security/main amd64 dnsutils all 1:9.18.47-1~deb12u1 [11.4 kB]
defender: Get:10 https://deb.debian.org/debian bookworm/main amd64 libblas3 amd64 3.11.0-2 [149 kB]
defender: Get:11 https://deb.debian.org/debian bookworm/main amd64 libdumbnet1 amd64 1.16.3-1 [27.5 kB]
defender: Get:12 https://deb.debian.org/debian bookworm/main amd64 liblinear4 amd64 2.3.0+dfsg-5 [43.6 kB]
defender: Get:13 https://deb.debian.org/debian bookworm/main amd64 liblua5.3-0 amd64 5.3.6-2 [123 kB]
defender: Get:14 https://deb.debian.org/debian bookworm/main amd64 libpcre3 amd64 2:8.39-15 [341 kB]
defender: Get:15 https://deb.debian.org/debian bookworm/main amd64 lua-lpeg amd64 1.0.2-2 [37.7 kB]
defender: Get:16 https://deb.debian.org/debian bookworm/main amd64 net-tools amd64 2.10-0.1+deb12u2 [243 kB]
defender: Get:17 https://deb.debian.org/debian bookworm/main amd64 netcat-openbsd amd64 1.219-1 [41.5 kB]
defender: Get:18 https://deb.debian.org/debian bookworm/main amd64 nmap-common all 7.93+dfsg1-1 [4148 kB]
defender: Get:19 https://deb.debian.org/debian bookworm/main amd64 nmap amd64 7.93+dfsg1-1 [1897 kB]
defender: Get:20 https://deb.debian.org/debian bookworm/main amd64 tcpreplay amd64 4.4.3-1 [325 kB]
defender: apt-listchanges: Reading changelogs...
defender: Preconfiguring packages ...
defender: /usr/bin/deb-systemd-helper was not called from dpkg. Exiting.
defender: /usr/bin/deb-systemd-helper was not called from dpkg. Exiting.
defender: Failed to stop iperf3.service: Unit iperf3.service not loaded.
defender: Fetched 10.1 MB in 36s (284 kB/s)
defender: Selecting previously unselected package libsctp1:amd64.
(Reading database ... 91194 files and directories currently installed.)
defender: Preparing to unpack .../00-libsctp1_1.0.19+dfsg-2_amd64.deb ...
defender: Unpacking libsctp1:amd64 (1.0.19+dfsg-2) ...
defender: Selecting previously unselected package libiperf0:amd64.
defender: Preparing to unpack .../01-libiperf0_3.12-1+deb12u2_amd64.deb ...
defender: Unpacking libiperf0:amd64 (3.12-1+deb12u2) ...
defender: Selecting previously unselected package iperf3.
defender: Preparing to unpack .../02-iperf3_3.12-1+deb12u2_amd64.deb ...
defender: Unpacking iperf3 (3.12-1+deb12u2) ...
defender: Preparing to unpack .../03-bind9-dnsutils_1%3a9.18.47-1~deb12u1_amd64.deb ...
defender: Unpacking bind9-dnsutils (1:9.18.47-1~deb12u1) over (1:9.18.28-1~deb12u2) ...
defender: Preparing to unpack .../04-bind9-host_1%3a9.18.47-1~deb12u1_amd64.deb ...
defender: Unpacking bind9-host (1:9.18.47-1~deb12u1) over (1:9.18.28-1~deb12u2) ...
defender: Preparing to unpack .../05-bind9-libs_1%3a9.18.47-1~deb12u1_amd64.deb ...
defender: Unpacking bind9-libs:amd64 (1:9.18.47-1~deb12u1) over (1:9.18.28-1~deb12u2) ...
defender: Selecting previously unselected package dnsutils.
defender: Preparing to unpack .../06-dnsutils_1%3a9.18.47-1~deb12u1_all.deb ...
defender: Unpacking dnsutils (1:9.18.47-1~deb12u1) ...
defender: Selecting previously unselected package libtcl8.6:amd64.
defender: Preparing to unpack .../07-libtcl8.6_8.6.13+dfsg-2_amd64.deb ...
defender: Unpacking libtcl8.6:amd64 (8.6.13+dfsg-2) ...
defender: Selecting previously unselected package hping3.
defender: Preparing to unpack .../08-hping3_3.a2.ds2-10_amd64.deb ...
defender: Unpacking hping3 (3.a2.ds2-10) ...
defender: Selecting previously unselected package libblas3:amd64.
defender: Preparing to unpack .../09-libblas3_3.11.0-2_amd64.deb ...
defender: Unpacking libblas3:amd64 (3.11.0-2) ...
defender: Selecting previously unselected package libdumbnet1:amd64.
defender: Preparing to unpack .../10-libdumbnet1_1.16.3-1_amd64.deb ...
defender: Unpacking libdumbnet1:amd64 (1.16.3-1) ...
defender: Selecting previously unselected package liblinear4:amd64.
defender: Preparing to unpack .../11-liblinear4_2.3.0+dfsg-5_amd64.deb ...
defender: Unpacking liblinear4:amd64 (2.3.0+dfsg-5) ...
defender: Selecting previously unselected package liblua5.3-0:amd64.
defender: Preparing to unpack .../12-liblua5.3-0_5.3.6-2_amd64.deb ...
defender: Unpacking liblua5.3-0:amd64 (5.3.6-2) ...
defender: Selecting previously unselected package libpcre3:amd64.
defender: Preparing to unpack .../13-libpcre3_2%3a8.39-15_amd64.deb ...
defender: Unpacking libpcre3:amd64 (2:8.39-15) ...
defender: Selecting previously unselected package lua-lpeg:amd64.
defender: Preparing to unpack .../14-lua-lpeg_1.0.2-2_amd64.deb ...
defender: Unpacking lua-lpeg:amd64 (1.0.2-2) ...
defender: Selecting previously unselected package net-tools.
defender: Preparing to unpack .../15-net-tools_2.10-0.1+deb12u2_amd64.deb ...
defender: Unpacking net-tools (2.10-0.1+deb12u2) ...
defender: Selecting previously unselected package netcat-openbsd.
defender: Preparing to unpack .../16-netcat-openbsd_1.219-1_amd64.deb ...
defender: Unpacking netcat-openbsd (1.219-1) ...
defender: Selecting previously unselected package nmap-common.
defender: Preparing to unpack .../17-nmap-common_7.93+dfsg1-1_all.deb ...
defender: Unpacking nmap-common (7.93+dfsg1-1) ...
defender: Selecting previously unselected package nmap.
defender: Preparing to unpack .../18-nmap_7.93+dfsg1-1_amd64.deb ...
defender: Unpacking nmap (7.93+dfsg1-1) ...
defender: Selecting previously unselected package tcpreplay.
defender: Preparing to unpack .../19-tcpreplay_4.4.3-1_amd64.deb ...
defender: Unpacking tcpreplay (4.4.3-1) ...
defender: Setting up net-tools (2.10-0.1+deb12u2) ...
defender: Setting up lua-lpeg:amd64 (1.0.2-2) ...
defender: Setting up bind9-libs:amd64 (1:9.18.47-1~deb12u1) ...
defender: Setting up netcat-openbsd (1.219-1) ...
defender: update-alternatives: using /bin/nc.openbsd to provide /bin/nc (nc) in auto mode
defender: Setting up libpcre3:amd64 (2:8.39-15) ...
defender: Setting up libblas3:amd64 (3.11.0-2) ...
defender: update-alternatives: using /usr/lib/x86_64-linux-gnu/blas/libblas.so.3 to provide /usr/lib/x86_64-linux-gnu/libblas.so.3 (libblas.so.3-x86_64-linux-gnu) in auto mode
defender: Setting up libtcl8.6:amd64 (8.6.13+dfsg-2) ...
defender: Setting up libdumbnet1:amd64 (1.16.3-1) ...
defender: Setting up libsctp1:amd64 (1.0.19+dfsg-2) ...
defender: Setting up nmap-common (7.93+dfsg1-1) ...
defender: Setting up liblua5.3-0:amd64 (5.3.6-2) ...
defender: Setting up hping3 (3.a2.ds2-10) ...
defender: Setting up bind9-host (1:9.18.47-1~deb12u1) ...
defender: Setting up liblinear4:amd64 (2.3.0+dfsg-5) ...
defender: Setting up tcpreplay (4.4.3-1) ...
defender: Setting up libiperf0:amd64 (3.12-1+deb12u2) ...
defender: Setting up bind9-dnsutils (1:9.18.47-1~deb12u1) ...
defender: Setting up iperf3 (3.12-1+deb12u2) ...
defender: Setting up dnsutils (1:9.18.47-1~deb12u1) ...
defender: Setting up nmap (7.93+dfsg1-1) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: +++ cmake --version
defender: +++ head -1
defender: +++ awk '{print $3}'
defender: ++ CMAKE_VERSION=3.25.1
defender: ++ '[' -z 3.25.1 ']'
defender: +++ printf '%s
defender: ' 3.20 3.25.1
defender: +++ sort -V
defender: +++ head -n1
defender: ++ '[' 3.20 '!=' 3.20 ']'
defender: +++ pkg-config --modversion libsodium
defender: 🔐 Installing libsodium 1.0.19 from source...
defender: ++ '[' 1.0.18 '!=' 1.0.19 ']'
defender: ++ echo '🔐 Installing libsodium 1.0.19 from source...'
defender: ++ cd /tmp
defender: ++ rm -rf libsodium-stable libsodium-1.0.19.tar.gz
defender: ++ curl -fsSL https://github.com/jedisct1/libsodium/releases/download/1.0.19-RELEASE/libsodium-1.0.19.tar.gz -o libsodium-1.0.19.tar.gz
defender: ++ tar xzf libsodium-1.0.19.tar.gz
defender: ++ cd libsodium-stable
defender: ++ ./configure --prefix=/usr/local
defender: checking build system type... x86_64-pc-linux-gnu
defender: checking host system type... x86_64-pc-linux-gnu
defender: checking target system type... x86_64-pc-linux-gnu
defender: checking for a BSD-compatible install... /usr/bin/install -c
defender: checking whether build environment is sane... yes
defender: checking for a race-free mkdir -p... /usr/bin/mkdir -p
defender: checking for gawk... no
defender: checking for mawk... mawk
defender: checking whether make sets $(MAKE)... yes
defender: checking whether make supports nested variables... yes
defender: checking whether UID '0' is supported by ustar format... yes
defender: checking whether GID '0' is supported by ustar format... yes
defender: checking how to create a ustar tar archive... gnutar
defender: checking whether make supports nested variables... (cached) yes
defender: checking whether to enable maintainer-specific portions of Makefiles... no
defender: checking for gcc... gcc
defender: checking whether the C compiler works... yes
defender: checking for C compiler default output file name... a.out
defender: checking for suffix of executables...
defender: checking whether we are cross compiling... no
defender: checking for suffix of object files... o
defender: checking whether the compiler supports GNU C... yes
defender: checking whether gcc accepts -g... yes
defender: checking for gcc option to enable C11 features... none needed
defender: checking whether gcc understands -c and -o together... yes
defender: checking whether make supports the include directive... yes (GNU style)
defender: checking dependency style of gcc... gcc3
defender: checking dependency style of gcc... gcc3
defender: checking for stdio.h... yes
defender: checking for stdlib.h... yes
defender: checking for string.h... yes
defender: checking for inttypes.h... yes
defender: checking for stdint.h... yes
defender: checking for strings.h... yes
defender: checking for sys/stat.h... yes
defender: checking for sys/types.h... yes
defender: checking for unistd.h... yes
defender: checking for wchar.h... yes
defender: checking for minix/config.h... no
defender: checking whether it is safe to define __EXTENSIONS__... yes
defender: checking whether _XOPEN_SOURCE should be defined... no
defender: checking whether C compiler accepts -Ofast... yes
defender: checking for a sed that does not truncate output... /usr/bin/sed
defender: checking how to run the C preprocessor... gcc -E
defender: checking for grep that handles long lines and -e... /usr/bin/grep
defender: checking for egrep... /usr/bin/grep -E
defender: checking whether gcc is Clang... no
defender: checking whether pthreads work with "-pthread" and "-lpthread"... yes
defender: checking for joinable pthread attribute... PTHREAD_CREATE_JOINABLE
defender: checking whether more special flags are required for pthreads... no
defender: checking for PTHREAD_PRIO_INHERIT... yes
defender: checking for variable-length arrays... yes
defender: checking for __wasi__ defined... no
defender: checking whether C compiler accepts -Werror... yes
defender: checking whether to add -D_FORTIFY_SOURCE=3 to CPPFLAGS... yes
defender: checking whether C compiler accepts -fvisibility=hidden... yes
defender: checking whether C compiler accepts -fPIC... yes
defender: checking whether C compiler accepts -fPIE... yes
defender: checking whether the linker accepts -pie... yes
defender: checking whether C compiler accepts -fno-strict-aliasing... yes
defender: checking whether C compiler accepts -fno-strict-overflow... yes
defender: checking whether C compiler accepts -fstack-protector... yes
defender: checking whether the linker accepts -fstack-protector... yes
defender: checking whether C compiler accepts  -Ofast -pthread -fvisibility=hidden -fPIC -fPIE -fno-strict-aliasing -fno-strict-overflow -fstack-protector -Wall... yes
defender: checking whether C compiler accepts  -Ofast -pthread -fvisibility=hidden -fPIC -fPIE -fno-strict-aliasing -fno-strict-overflow -fstack-protector -Wno-deprecated-declarations... yes                                                                                                                                                                                            
defender: checking whether C compiler accepts  -Ofast -pthread -fvisibility=hidden -fPIC -fPIE -fno-strict-aliasing -fno-strict-overflow -fstack-protector -Wno-deprecated-declarations -Wno-unknown-pragmas... yes                                                                                                                                                                       
defender: checking for clang... no
defender: checking whether C compiler accepts  -Ofast -pthread -fvisibility=hidden -fPIC -fPIE -fno-strict-aliasing -fno-strict-overflow -fstack-protector -Wall -Wextra... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2... yes
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op... yes                                                                                                                                                                                  
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized... yes                                                                                                                                                            
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation... yes                                                                                                                                   
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations... yes                                                                                                            
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes... yes                                                                                       
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs... yes                                                                      
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits... yes                                                     
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas... yes                                
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id... yes                
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference... yes                                                                                                                                                                                            
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration... yes                                                                                                                                                                    
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith... yes                                                                                                                                                    
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls... yes                                                                                                                                  
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict... yes                                                                                                                       
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict -Wshorten-64-to-32... no                                                                                                     
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict -Wsometimes-uninitialized... no                                                                                              
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict -Wstrict-prototypes... yes                                                                                                   
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict -Wstrict-prototypes -Wswitch-enum... yes                                                                                     
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict -Wstrict-prototypes -Wswitch-enum -Wvariable-decl... no                                                                      
defender: checking whether C compiler accepts  -Wextra -Warray-bounds -Wbad-function-cast -Wcast-qual -Wdiv-by-zero -Wduplicated-branches -Wduplicated-cond -Wfloat-equal -Wformat=2 -Wlogical-op -Wmaybe-uninitialized -Wmisleading-indentation -Wmissing-declarations -Wmissing-prototypes -Wnested-externs -Wno-type-limits -Wno-unknown-pragmas -Wnormalized=id -Wnull-dereference -Wold-style-declaration -Wpointer-arith -Wredundant-decls -Wrestrict -Wstrict-prototypes -Wswitch-enum -Wwrite-strings... yes                                                                     
defender: checking whether the linker accepts -Wl,-z,relro... yes
defender: checking whether the linker accepts -Wl,-z,now... yes
defender: checking whether the linker accepts -Wl,-z,noexecstack... yes
defender: checking whether segmentation violations can be caught... yes
defender: checking whether SIGABRT can be caught... yes
defender: checking for thread local storage (TLS) class... _Thread_local
defender: thread local storage is supported
defender: checking whether C compiler accepts -ftls-model=local-dynamic... yes
defender: checking how to print strings... printf
defender: checking for a sed that does not truncate output... (cached) /usr/bin/sed
defender: checking for fgrep... /usr/bin/grep -F
defender: checking for ld used by gcc... /usr/bin/ld
defender: checking if the linker (/usr/bin/ld) is GNU ld... yes
defender: checking for BSD- or MS-compatible name lister (nm)... /usr/bin/nm -B
defender: checking the name lister (/usr/bin/nm -B) interface... BSD nm
defender: checking whether ln -s works... yes
defender: checking the maximum length of command line arguments... 1572864
defender: checking how to convert x86_64-pc-linux-gnu file names to x86_64-pc-linux-gnu format... func_convert_file_noop
defender: checking how to convert x86_64-pc-linux-gnu file names to toolchain format... func_convert_file_noop
defender: checking for /usr/bin/ld option to reload object files... -r
defender: checking for file... file
defender: checking for objdump... objdump
defender: checking how to recognize dependent libraries... pass_all
defender: checking for dlltool... no
defender: checking how to associate runtime and link libraries... printf %s\n
defender: checking for ar... ar
defender: checking for archiver @FILE support... @
defender: checking for strip... strip
defender: checking for ranlib... ranlib
defender: checking command to parse /usr/bin/nm -B output from gcc object... ok
defender: checking for sysroot... no
defender: checking for a working dd... /usr/bin/dd
defender: checking how to truncate binary pipes... /usr/bin/dd bs=4096 count=1
defender: checking for mt... mt
defender: checking if mt is a manifest tool... no
defender: checking for dlfcn.h... yes
defender: checking for objdir... .libs
defender: checking if gcc supports -fno-rtti -fno-exceptions... no
defender: checking for gcc option to produce PIC... -fPIC -DPIC
defender: checking if gcc PIC flag -fPIC -DPIC works... yes
defender: checking if gcc static flag -static works... yes
defender: checking if gcc supports -c -o file.o... yes
defender: checking if gcc supports -c -o file.o... (cached) yes
defender: checking whether the gcc linker (/usr/bin/ld -m elf_x86_64) supports shared libraries... yes
defender: checking whether -lc should be explicitly linked in... no
defender: checking dynamic linker characteristics... GNU/Linux ld.so
defender: checking how to hardcode library paths into programs... immediate
defender: checking whether stripping libraries is possible... yes
defender: checking if libtool supports shared libraries... yes
defender: checking whether to build shared libraries... yes
defender: checking whether to build static libraries... yes
defender: checking for ar... (cached) ar
defender: checking for ARM64 target... no
defender: checking whether C compiler accepts -mmmx... yes
defender: checking for MMX instructions set... yes
defender: checking whether C compiler accepts -mmmx... (cached) yes
defender: checking whether C compiler accepts -msse2... yes
defender: checking for SSE2 instructions set... yes
defender: checking whether C compiler accepts -msse2... (cached) yes
defender: checking whether C compiler accepts -msse3... yes
defender: checking for SSE3 instructions set... yes
defender: checking whether C compiler accepts -msse3... (cached) yes
defender: checking whether C compiler accepts -mssse3... yes
defender: checking for SSSE3 instructions set... yes
defender: checking whether C compiler accepts -mssse3... (cached) yes
defender: checking whether C compiler accepts -msse4.1... yes
defender: checking for SSE4.1 instructions set... yes
defender: checking whether C compiler accepts -msse4.1... (cached) yes
defender: checking whether C compiler accepts -mavx... yes
defender: checking for AVX instructions set... yes
defender: checking whether C compiler accepts -mavx... (cached) yes
defender: checking whether C compiler accepts -mavx2... yes
defender: checking for AVX2 instructions set... yes
defender: checking whether C compiler accepts -mavx2... (cached) yes
defender: checking if _mm256_broadcastsi128_si256 is correctly defined... yes
defender: checking whether C compiler accepts -mavx512f... yes
defender: checking for AVX512F instructions set... yes
defender: checking whether C compiler accepts -mavx512f... (cached) yes
defender: checking whether C compiler accepts -maes... yes
defender: checking whether C compiler accepts -mpclmul... yes
defender: checking for AESNI instructions set and PCLMULQDQ... yes
defender: checking whether C compiler accepts -maes... (cached) yes
defender: checking whether C compiler accepts -mpclmul... (cached) yes
defender: checking whether C compiler accepts -mrdrnd... yes
defender: checking for RDRAND... yes
defender: checking whether C compiler accepts -mrdrnd... (cached) yes
defender: checking for sys/mman.h... yes
defender: checking for sys/param.h... yes
defender: checking for sys/random.h... yes
defender: checking for intrin.h... no
defender: checking for sys/auxv.h... yes
defender: checking for CommonCrypto/CommonRandom.h... no
defender: checking for cet.h... yes
defender: checking if _xgetbv() is available... no
defender: checking for inline... inline
defender: checking whether byte ordering is bigendian... (cached) no
defender: checking whether __STDC_LIMIT_MACROS is required... no
defender: checking whether we can use inline asm code... yes
defender: no
defender: checking whether we can use x86_64 asm code... yes
defender: checking whether we can assemble AVX opcodes... yes
defender: checking for 128-bit arithmetic... yes
defender: checking for cpuid instruction... yes
defender: checking if the .private_extern asm directive is supported... no
defender: checking if the .hidden asm directive is supported... yes
defender: checking if weak symbols are supported... yes
defender: checking if atomic operations are supported... yes
defender: checking if C11 memory fences are supported... yes
defender: checking if gcc memory fences are supported... yes
defender: checking for size_t... yes
defender: checking for working alloca.h... yes
defender: checking for alloca... yes
defender: checking for arc4random... yes
defender: checking for arc4random_buf... yes
defender: checking for mmap... yes
defender: checking for mlock... yes
defender: checking for madvise... yes
defender: checking for mprotect... yes
defender: checking for raise... yes
defender: checking for sysconf... yes
defender: checking for getrandom with a standard API... yes
defender: checking for getrandom... yes
defender: checking for getentropy with a standard API... yes
defender: checking for getentropy... yes
defender: checking for getpid... yes
defender: checking for getauxval... yes
defender: checking for elf_aux_info... no
defender: checking for posix_memalign... yes
defender: checking for nanosleep... yes
defender: checking for clock_gettime... yes
defender: checking for memset_s... no
defender: checking for explicit_bzero... yes
defender: checking for memset_explicit... no
defender: checking for explicit_memset... no
defender: checking if gcc/ld supports -Wl,--output-def... no
defender: checking that generated files are newer than configure... done
defender: configure: creating ./config.status
defender: config.status: creating Makefile
defender: config.status: creating builds/Makefile
defender: config.status: creating contrib/Makefile
defender: config.status: creating dist-build/Makefile
defender: config.status: creating libsodium.pc
defender: config.status: creating libsodium-uninstalled.pc
defender: config.status: creating src/Makefile
defender: config.status: creating src/libsodium/Makefile
defender: config.status: creating src/libsodium/include/Makefile
defender: config.status: creating src/libsodium/include/sodium/version.h
defender: config.status: creating test/default/Makefile
defender: config.status: creating test/Makefile
defender: config.status: executing depfiles commands
defender: config.status: executing libtool commands
defender: ++ make -j4
defender: Making all in builds
defender: make[1]: Entering directory '/tmp/libsodium-stable/builds'
defender: make[1]: Nothing to be done for 'all'.
defender: make[1]: Leaving directory '/tmp/libsodium-stable/builds'
defender: Making all in contrib
defender: make[1]: Entering directory '/tmp/libsodium-stable/contrib'
defender: make[1]: Nothing to be done for 'all'.
defender: make[1]: Leaving directory '/tmp/libsodium-stable/contrib'
defender: Making all in dist-build
defender: make[1]: Entering directory '/tmp/libsodium-stable/dist-build'
defender: make[1]: Nothing to be done for 'all'.
defender: make[1]: Leaving directory '/tmp/libsodium-stable/dist-build'
defender: Making all in src
defender: make[1]: Entering directory '/tmp/libsodium-stable/src'
defender: Making all in libsodium
defender: make[2]: Entering directory '/tmp/libsodium-stable/src/libsodium'
defender: Making all in include
defender: make[3]: Entering directory '/tmp/libsodium-stable/src/libsodium/include'
defender: make[3]: Nothing to be done for 'all'.
defender: make[3]: Leaving directory '/tmp/libsodium-stable/src/libsodium/include'
defender: make[3]: Entering directory '/tmp/libsodium-stable/src/libsodium'
defender:   CC       crypto_shorthash/siphash24/libsodium_la-shorthash_siphashx24.lo
defender:   CC       crypto_shorthash/siphash24/ref/libsodium_la-shorthash_siphashx24_ref.lo
defender:   CC       crypto_sign/ed25519/ref10/libsodium_la-obsolete.lo
defender:   CC       crypto_aead/aegis128l/libaesni_la-aegis128l_aesni.lo
defender:   CC       crypto_aead/aegis256/libaesni_la-aegis256_aesni.lo
defender:   CC       crypto_aead/aegis128l/libarmcrypto_la-aegis128l_armcrypto.lo
defender:   CC       crypto_aead/aegis256/libarmcrypto_la-aegis256_armcrypto.lo
defender:   CC       crypto_generichash/blake2b/ref/libssse3_la-blake2b-compress-ssse3.lo
defender:   CC       crypto_pwhash/argon2/libssse3_la-argon2-fill-block-ssse3.lo
defender:   CC       crypto_generichash/blake2b/ref/libsse41_la-blake2b-compress-sse41.lo
defender:   CC       crypto_generichash/blake2b/ref/libavx2_la-blake2b-compress-avx2.lo
defender:   CC       crypto_pwhash/argon2/libavx2_la-argon2-fill-block-avx2.lo
defender:   CC       crypto_stream/chacha20/dolbeau/libavx2_la-chacha20_dolbeau-avx2.lo
defender:   CC       crypto_pwhash/argon2/libavx512f_la-argon2-fill-block-avx512f.lo
defender:   CC       crypto_aead/aegis128l/libsodium_la-aead_aegis128l.lo
defender:   CC       crypto_aead/aegis128l/libsodium_la-aegis128l_soft.lo
defender:   CC       crypto_aead/aegis256/libsodium_la-aead_aegis256.lo
defender:   CC       crypto_aead/aegis256/libsodium_la-aegis256_soft.lo
defender:   CC       crypto_aead/aes256gcm/libsodium_la-aead_aes256gcm.lo
defender:   CC       crypto_aead/chacha20poly1305/libsodium_la-aead_chacha20poly1305.lo
defender:   CC       crypto_aead/xchacha20poly1305/libsodium_la-aead_xchacha20poly1305.lo
defender:   CC       crypto_auth/libsodium_la-crypto_auth.lo
defender:   CC       crypto_auth/hmacsha256/libsodium_la-auth_hmacsha256.lo
defender:   CC       crypto_auth/hmacsha512/libsodium_la-auth_hmacsha512.lo
defender:   CC       crypto_auth/hmacsha512256/libsodium_la-auth_hmacsha512256.lo
defender:   CC       crypto_box/libsodium_la-crypto_box.lo
defender:   CC       crypto_box/libsodium_la-crypto_box_easy.lo
defender:   CC       crypto_box/libsodium_la-crypto_box_seal.lo
defender:   CC       crypto_box/curve25519xsalsa20poly1305/libsodium_la-box_curve25519xsalsa20poly1305.lo
defender:   CC       crypto_core/ed25519/ref10/libsodium_la-ed25519_ref10.lo
defender:   CC       crypto_core/hchacha20/libsodium_la-core_hchacha20.lo
defender:   CC       crypto_core/hsalsa20/ref2/libsodium_la-core_hsalsa20_ref2.lo
defender:   CC       crypto_core/hsalsa20/libsodium_la-core_hsalsa20.lo
defender:   CC       crypto_core/salsa/ref/libsodium_la-core_salsa_ref.lo
defender:   CC       crypto_core/softaes/libsodium_la-softaes.lo
defender:   CC       crypto_generichash/libsodium_la-crypto_generichash.lo
defender:   CC       crypto_generichash/blake2b/libsodium_la-generichash_blake2.lo
defender:   CC       crypto_generichash/blake2b/ref/libsodium_la-blake2b-compress-ref.lo
defender:   CC       crypto_generichash/blake2b/ref/libsodium_la-blake2b-ref.lo
defender:   CC       crypto_generichash/blake2b/ref/libsodium_la-generichash_blake2b.lo
defender:   CC       crypto_hash/libsodium_la-crypto_hash.lo
defender:   CC       crypto_hash/sha256/libsodium_la-hash_sha256.lo
defender:   CC       crypto_hash/sha256/cp/libsodium_la-hash_sha256_cp.lo
defender:   CC       crypto_hash/sha512/libsodium_la-hash_sha512.lo
defender:   CC       crypto_hash/sha512/cp/libsodium_la-hash_sha512_cp.lo
defender:   CC       crypto_kdf/blake2b/libsodium_la-kdf_blake2b.lo
defender:   CC       crypto_kdf/libsodium_la-crypto_kdf.lo
defender:   CC       crypto_kdf/hkdf/libsodium_la-kdf_hkdf_sha256.lo
defender:   CC       crypto_kdf/hkdf/libsodium_la-kdf_hkdf_sha512.lo
defender:   CC       crypto_kx/libsodium_la-crypto_kx.lo
defender:   CC       crypto_onetimeauth/libsodium_la-crypto_onetimeauth.lo
defender:   CC       crypto_onetimeauth/poly1305/libsodium_la-onetimeauth_poly1305.lo
defender:   CC       crypto_onetimeauth/poly1305/donna/libsodium_la-poly1305_donna.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-argon2-core.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-argon2-encoding.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-argon2-fill-block-ref.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-argon2.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-blake2b-long.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-pwhash_argon2i.lo
defender:   CC       crypto_pwhash/argon2/libsodium_la-pwhash_argon2id.lo
defender:   CC       crypto_pwhash/libsodium_la-crypto_pwhash.lo
defender:   CC       crypto_scalarmult/libsodium_la-crypto_scalarmult.lo
defender:   CC       crypto_scalarmult/curve25519/ref10/libsodium_la-x25519_ref10.lo
defender:   CC       crypto_scalarmult/curve25519/libsodium_la-scalarmult_curve25519.lo
defender:   CC       crypto_secretbox/libsodium_la-crypto_secretbox.lo
defender:   CC       crypto_secretbox/libsodium_la-crypto_secretbox_easy.lo
defender:   CC       crypto_secretbox/xsalsa20poly1305/libsodium_la-secretbox_xsalsa20poly1305.lo
defender:   CC       crypto_secretstream/xchacha20poly1305/libsodium_la-secretstream_xchacha20poly1305.lo
defender:   CC       crypto_shorthash/libsodium_la-crypto_shorthash.lo
defender:   CC       crypto_shorthash/siphash24/libsodium_la-shorthash_siphash24.lo
defender:   CC       crypto_shorthash/siphash24/ref/libsodium_la-shorthash_siphash24_ref.lo
defender:   CC       crypto_sign/libsodium_la-crypto_sign.lo
defender:   CC       crypto_sign/ed25519/libsodium_la-sign_ed25519.lo
defender:   CC       crypto_sign/ed25519/ref10/libsodium_la-keypair.lo
defender:   CC       crypto_sign/ed25519/ref10/libsodium_la-open.lo
defender:   CC       crypto_sign/ed25519/ref10/libsodium_la-sign.lo
defender:   CC       crypto_stream/chacha20/libsodium_la-stream_chacha20.lo
defender:   CC       crypto_stream/chacha20/ref/libsodium_la-chacha20_ref.lo
defender:   CC       crypto_stream/libsodium_la-crypto_stream.lo
defender:   CC       crypto_stream/salsa20/libsodium_la-stream_salsa20.lo
defender:   CC       crypto_stream/xsalsa20/libsodium_la-stream_xsalsa20.lo
defender:   CC       crypto_verify/libsodium_la-verify.lo
defender:   CC       randombytes/libsodium_la-randombytes.lo
defender:   CC       sodium/libsodium_la-codecs.lo
defender:   CC       sodium/libsodium_la-core.lo
defender:   CC       sodium/libsodium_la-runtime.lo
defender:   CC       sodium/libsodium_la-utils.lo
defender:   CC       sodium/libsodium_la-version.lo
defender:   CPPAS    crypto_stream/salsa20/xmm6/libsodium_la-salsa20_xmm6-asm.lo
defender:   CC       crypto_stream/salsa20/xmm6/libsodium_la-salsa20_xmm6.lo
defender:   CC       crypto_scalarmult/curve25519/sandy2x/libsodium_la-curve25519_sandy2x.lo
defender:   CC       crypto_scalarmult/curve25519/sandy2x/libsodium_la-fe51_invert.lo
defender:   CC       crypto_scalarmult/curve25519/sandy2x/libsodium_la-fe_frombytes_sandy2x.lo
defender:   CPPAS    crypto_scalarmult/curve25519/sandy2x/libsodium_la-sandy2x.lo
defender:   CC       crypto_box/curve25519xchacha20poly1305/libsodium_la-box_curve25519xchacha20poly1305.lo
defender:   CC       crypto_box/curve25519xchacha20poly1305/libsodium_la-box_seal_curve25519xchacha20poly1305.lo
defender:   CC       crypto_core/ed25519/libsodium_la-core_ed25519.lo
defender:   CC       crypto_core/ed25519/libsodium_la-core_ristretto255.lo
defender:   CC       crypto_pwhash/scryptsalsa208sha256/libsodium_la-crypto_scrypt-common.lo
defender:   CC       crypto_pwhash/scryptsalsa208sha256/libsodium_la-scrypt_platform.lo
defender:   CC       crypto_pwhash/scryptsalsa208sha256/libsodium_la-pbkdf2-sha256.lo
defender:   CC       crypto_pwhash/scryptsalsa208sha256/libsodium_la-pwhash_scryptsalsa208sha256.lo
defender:   CC       crypto_pwhash/scryptsalsa208sha256/nosse/libsodium_la-pwhash_scryptsalsa208sha256_nosse.lo
defender:   CC       crypto_scalarmult/ed25519/ref10/libsodium_la-scalarmult_ed25519_ref10.lo
defender:   CC       crypto_scalarmult/ristretto255/ref10/libsodium_la-scalarmult_ristretto255_ref10.lo
defender:   CC       crypto_secretbox/xchacha20poly1305/libsodium_la-secretbox_xchacha20poly1305.lo
defender:   CC       crypto_stream/salsa2012/ref/libsodium_la-stream_salsa2012_ref.lo
defender:   CC       crypto_stream/salsa2012/libsodium_la-stream_salsa2012.lo
defender:   CC       crypto_stream/salsa208/ref/libsodium_la-stream_salsa208_ref.lo
defender:   CC       crypto_stream/salsa208/libsodium_la-stream_salsa208.lo
defender:   CC       crypto_stream/xchacha20/libsodium_la-stream_xchacha20.lo
defender:   CC       randombytes/sysrandom/libsodium_la-randombytes_sysrandom.lo
defender:   CC       crypto_aead/aes256gcm/aesni/libaesni_la-aead_aes256gcm_aesni.lo
defender:   CC       crypto_aead/aes256gcm/armcrypto/libarmcrypto_la-aead_aes256gcm_armcrypto.lo
defender:   CC       crypto_onetimeauth/poly1305/sse2/libsse2_la-poly1305_sse2.lo
defender:   CC       crypto_pwhash/scryptsalsa208sha256/sse/libsse2_la-pwhash_scryptsalsa208sha256_sse.lo
defender:   CC       crypto_stream/chacha20/dolbeau/libssse3_la-chacha20_dolbeau-ssse3.lo
defender:   CCLD     libsse41.la
defender:   CC       crypto_stream/salsa20/xmm6int/libavx2_la-salsa20_xmm6int-avx2.lo
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CCLD     libavx512f.la
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CC       randombytes/internal/librdrand_la-randombytes_internal_random.lo
defender:   CCLD     libarmcrypto.la
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CCLD     libsse2.la
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CCLD     libssse3.la
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CCLD     libavx2.la
defender:   CCLD     librdrand.la
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CCLD     libaesni.la
defender: libtool: warning: '-version-info/-version-number' is ignored for convenience libraries
defender:   CCLD     libsodium.la
defender: make[3]: Leaving directory '/tmp/libsodium-stable/src/libsodium'
defender: make[2]: Leaving directory '/tmp/libsodium-stable/src/libsodium'
defender: make[2]: Entering directory '/tmp/libsodium-stable/src'
defender: make[2]: Nothing to be done for 'all-am'.
defender: make[2]: Leaving directory '/tmp/libsodium-stable/src'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/src'
defender: Making all in test
defender: make[1]: Entering directory '/tmp/libsodium-stable/test'
defender: Making all in default
defender: make[2]: Entering directory '/tmp/libsodium-stable/test/default'
defender: make[2]: Nothing to be done for 'all'.
defender: make[2]: Leaving directory '/tmp/libsodium-stable/test/default'
defender: make[2]: Entering directory '/tmp/libsodium-stable/test'
defender: make[2]: Nothing to be done for 'all-am'.
defender: make[2]: Leaving directory '/tmp/libsodium-stable/test'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/test'
defender: make[1]: Entering directory '/tmp/libsodium-stable'
defender: make[1]: Nothing to be done for 'all-am'.
defender: make[1]: Leaving directory '/tmp/libsodium-stable'
defender: ++ make install
defender: Making install in builds
defender: make[1]: Entering directory '/tmp/libsodium-stable/builds'
defender: make[2]: Entering directory '/tmp/libsodium-stable/builds'
defender: make[2]: Nothing to be done for 'install-exec-am'.
defender: make[2]: Nothing to be done for 'install-data-am'.
defender: make[2]: Leaving directory '/tmp/libsodium-stable/builds'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/builds'
defender: Making install in contrib
defender: make[1]: Entering directory '/tmp/libsodium-stable/contrib'
defender: make[2]: Entering directory '/tmp/libsodium-stable/contrib'
defender: make[2]: Nothing to be done for 'install-exec-am'.
defender: make[2]: Nothing to be done for 'install-data-am'.
defender: make[2]: Leaving directory '/tmp/libsodium-stable/contrib'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/contrib'
defender: Making install in dist-build
defender: make[1]: Entering directory '/tmp/libsodium-stable/dist-build'
defender: make[2]: Entering directory '/tmp/libsodium-stable/dist-build'
defender: make[2]: Nothing to be done for 'install-exec-am'.
defender: make[2]: Nothing to be done for 'install-data-am'.
defender: make[2]: Leaving directory '/tmp/libsodium-stable/dist-build'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/dist-build'
defender: Making install in src
defender: make[1]: Entering directory '/tmp/libsodium-stable/src'
defender: Making install in libsodium
defender: make[2]: Entering directory '/tmp/libsodium-stable/src/libsodium'
defender: Making install in include
defender: make[3]: Entering directory '/tmp/libsodium-stable/src/libsodium/include'
defender: make[4]: Entering directory '/tmp/libsodium-stable/src/libsodium/include'
defender: make[4]: Nothing to be done for 'install-exec-am'.
defender:  /usr/bin/mkdir -p '/usr/local/include'
defender:  /usr/bin/mkdir -p '/usr/local/include/sodium'
defender:  /usr/bin/install -c -m 644  sodium/core.h sodium/crypto_aead_aes256gcm.h sodium/crypto_aead_aegis128l.h sodium/crypto_aead_aegis256.h sodium/crypto_aead_chacha20poly1305.h sodium/crypto_aead_xchacha20poly1305.h sodium/crypto_auth.h sodium/crypto_auth_hmacsha256.h sodium/crypto_auth_hmacsha512.h sodium/crypto_auth_hmacsha512256.h sodium/crypto_box.h sodium/crypto_box_curve25519xchacha20poly1305.h sodium/crypto_box_curve25519xsalsa20poly1305.h sodium/crypto_core_ed25519.h sodium/crypto_core_ristretto255.h sodium/crypto_core_hchacha20.h sodium/crypto_core_hsalsa20.h sodium/crypto_core_salsa20.h sodium/crypto_core_salsa2012.h sodium/crypto_core_salsa208.h sodium/crypto_generichash.h sodium/crypto_generichash_blake2b.h sodium/crypto_hash.h sodium/crypto_hash_sha256.h sodium/crypto_hash_sha512.h sodium/crypto_kdf.h sodium/crypto_kdf_hkdf_sha256.h sodium/crypto_kdf_hkdf_sha512.h sodium/crypto_kdf_blake2b.h sodium/crypto_kx.h sodium/crypto_onetimeauth.h sodium/crypto_onetimeauth_poly1305.h sodium/crypto_pwhash.h sodium/crypto_pwhash_argon2i.h sodium/crypto_pwhash_argon2id.h sodium/crypto_pwhash_scryptsalsa208sha256.h sodium/crypto_scalarmult.h sodium/crypto_scalarmult_curve25519.h sodium/crypto_scalarmult_ed25519.h sodium/crypto_scalarmult_ristretto255.h '/usr/local/include/sodium'                            
defender:  /usr/bin/mkdir -p '/usr/local/include/sodium'
defender:  /usr/bin/install -c -m 644  sodium/crypto_secretbox.h sodium/crypto_secretbox_xchacha20poly1305.h sodium/crypto_secretbox_xsalsa20poly1305.h sodium/crypto_secretstream_xchacha20poly1305.h sodium/crypto_shorthash.h sodium/crypto_shorthash_siphash24.h sodium/crypto_sign.h sodium/crypto_sign_ed25519.h sodium/crypto_sign_edwards25519sha512batch.h sodium/crypto_stream.h sodium/crypto_stream_chacha20.h sodium/crypto_stream_salsa20.h sodium/crypto_stream_salsa2012.h sodium/crypto_stream_salsa208.h sodium/crypto_stream_xchacha20.h sodium/crypto_stream_xsalsa20.h sodium/crypto_verify_16.h sodium/crypto_verify_32.h sodium/crypto_verify_64.h sodium/export.h sodium/randombytes.h sodium/randombytes_internal_random.h sodium/randombytes_sysrandom.h sodium/runtime.h sodium/utils.h '/usr/local/include/sodium'                                                                                                                                         
defender:  /usr/bin/install -c -m 644  sodium.h '/usr/local/include/.'
defender:  /usr/bin/mkdir -p '/usr/local/include'
defender:  /usr/bin/mkdir -p '/usr/local/include/sodium'
defender:  /usr/bin/install -c -m 644  sodium/version.h '/usr/local/include/sodium'
defender: make[4]: Leaving directory '/tmp/libsodium-stable/src/libsodium/include'
defender: make[3]: Leaving directory '/tmp/libsodium-stable/src/libsodium/include'
defender: make[3]: Entering directory '/tmp/libsodium-stable/src/libsodium'
defender: make[4]: Entering directory '/tmp/libsodium-stable/src/libsodium'
defender:  /usr/bin/mkdir -p '/usr/local/lib'
defender:  /bin/bash ../../libtool   --mode=install /usr/bin/install -c   libsodium.la '/usr/local/lib'
defender: libtool: install: /usr/bin/install -c .libs/libsodium.so.26.1.0 /usr/local/lib/libsodium.so.26.1.0
defender: libtool: install: (cd /usr/local/lib && { ln -s -f libsodium.so.26.1.0 libsodium.so.26 || { rm -f libsodium.so.26 && ln -s libsodium.so.26.1.0 libsodium.so.26; }; })
defender: libtool: install: (cd /usr/local/lib && { ln -s -f libsodium.so.26.1.0 libsodium.so || { rm -f libsodium.so && ln -s libsodium.so.26.1.0 libsodium.so; }; })
defender: libtool: install: /usr/bin/install -c .libs/libsodium.lai /usr/local/lib/libsodium.la
defender: libtool: install: /usr/bin/install -c .libs/libsodium.a /usr/local/lib/libsodium.a
defender: libtool: install: chmod 644 /usr/local/lib/libsodium.a
defender: libtool: install: ranlib /usr/local/lib/libsodium.a
defender: libtool: finish: PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/sbin" ldconfig -n /usr/local/lib
defender: ----------------------------------------------------------------------
defender: Libraries have been installed in:
defender:    /usr/local/lib
defender:
defender: If you ever happen to want to link against installed libraries
defender: in a given directory, LIBDIR, you must either use libtool, and
defender: specify the full pathname of the library, or use the '-LLIBDIR'
defender: flag during linking and do at least one of the following:
defender:    - add LIBDIR to the 'LD_LIBRARY_PATH' environment variable
defender:      during execution
defender:    - add LIBDIR to the 'LD_RUN_PATH' environment variable
defender:      during linking
defender:    - use the '-Wl,-rpath -Wl,LIBDIR' linker flag
defender:    - have your system administrator add LIBDIR to '/etc/ld.so.conf'
defender:
defender: See any operating system documentation about shared libraries for
defender: more information, such as the ld(1) and ld.so(8) manual pages.
defender: ----------------------------------------------------------------------
defender: make[4]: Nothing to be done for 'install-data-am'.
defender: make[4]: Leaving directory '/tmp/libsodium-stable/src/libsodium'
defender: make[3]: Leaving directory '/tmp/libsodium-stable/src/libsodium'
defender: make[2]: Leaving directory '/tmp/libsodium-stable/src/libsodium'
defender: make[2]: Entering directory '/tmp/libsodium-stable/src'
defender: make[3]: Entering directory '/tmp/libsodium-stable/src'
defender: make[3]: Nothing to be done for 'install-exec-am'.
defender: make[3]: Nothing to be done for 'install-data-am'.
defender: make[3]: Leaving directory '/tmp/libsodium-stable/src'
defender: make[2]: Leaving directory '/tmp/libsodium-stable/src'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/src'
defender: Making install in test
defender: make[1]: Entering directory '/tmp/libsodium-stable/test'
defender: Making install in default
defender: make[2]: Entering directory '/tmp/libsodium-stable/test/default'
defender: make[3]: Entering directory '/tmp/libsodium-stable/test/default'
defender: make[3]: Nothing to be done for 'install-exec-am'.
defender: make[3]: Nothing to be done for 'install-data-am'.
defender: make[3]: Leaving directory '/tmp/libsodium-stable/test/default'
defender: make[2]: Leaving directory '/tmp/libsodium-stable/test/default'
defender: make[2]: Entering directory '/tmp/libsodium-stable/test'
defender: make[3]: Entering directory '/tmp/libsodium-stable/test'
defender: make[3]: Nothing to be done for 'install-exec-am'.
defender: make[3]: Nothing to be done for 'install-data-am'.
defender: make[3]: Leaving directory '/tmp/libsodium-stable/test'
defender: make[2]: Leaving directory '/tmp/libsodium-stable/test'
defender: make[1]: Leaving directory '/tmp/libsodium-stable/test'
defender: make[1]: Entering directory '/tmp/libsodium-stable'
defender: make[2]: Entering directory '/tmp/libsodium-stable'
defender: make[2]: Nothing to be done for 'install-exec-am'.
defender:  /usr/bin/mkdir -p '/usr/local/lib/pkgconfig'
defender:  /usr/bin/install -c -m 644 libsodium.pc '/usr/local/lib/pkgconfig'
defender: make[2]: Leaving directory '/tmp/libsodium-stable'
defender: make[1]: Leaving directory '/tmp/libsodium-stable'
defender: ++ ldconfig
defender: +++ pkg-config --modversion libsodium
defender: ✅ libsodium 1.0.19 installed
defender: 🧠 Installing ONNX Runtime v1.17.1...
defender: ++ echo '✅ libsodium 1.0.19 installed'
defender: ++ '[' '!' -f /usr/local/lib/libonnxruntime.so ']'
defender: ++ echo '🧠 Installing ONNX Runtime v1.17.1...'
defender: ++ cd /tmp
defender: ++ wget -q https://github.com/microsoft/onnxruntime/releases/download/v1.17.1/onnxruntime-linux-x64-1.17.1.tgz
defender: ++ tar -xzf onnxruntime-linux-x64-1.17.1.tgz
defender: ++ cp -r onnxruntime-linux-x64-1.17.1/include/cpu_provider_factory.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_c_api.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_cxx_api.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_cxx_inline.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_float16.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_run_options_config_keys.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_session_options_config_keys.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_training_c_api.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_training_cxx_api.h onnxruntime-linux-x64-1.17.1/include/onnxruntime_training_cxx_inline.h onnxruntime-linux-x64-1.17.1/include/provider_options.h /usr/local/include/          
defender: ++ cp -r onnxruntime-linux-x64-1.17.1/lib/libonnxruntime.so onnxruntime-linux-x64-1.17.1/lib/libonnxruntime.so.1.17.1 /usr/local/lib/
defender: ++ ldconfig
defender: 🔗 Creating /usr/local/lib64 symlinks for ONNX Runtime...
defender: ++ echo '🔗 Creating /usr/local/lib64 symlinks for ONNX Runtime...'
defender: ++ mkdir -p /usr/local/lib64
defender: ++ ln -sf /usr/local/lib/libonnxruntime.so /usr/local/lib/libonnxruntime.so.1.17.1 /usr/local/lib64/
defender: ++ ln -sf /usr/local/lib/libonnxruntime_providers_shared.so /usr/local/lib64/
defender: ++ rm -rf onnxruntime-linux-x64-1.17.1 onnxruntime-linux-x64-1.17.1.tgz
defender: ✅ ONNX Runtime installed with lib64 symlinks
defender: 🔍 Installing FAISS v1.8.0 (CPU-only, shared library)...
defender: ++ echo '✅ ONNX Runtime installed with lib64 symlinks'
defender: ++ '[' '!' -f /usr/local/lib/libfaiss.so ']'
defender: ++ echo '🔍 Installing FAISS v1.8.0 (CPU-only, shared library)...'
defender: ++ apt-get install -y libblas-dev liblapack-dev
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   liblapack3
defender: Suggested packages:
defender:   liblapack-doc
defender: The following NEW packages will be installed:
defender:   libblas-dev liblapack-dev liblapack3
defender: 0 upgraded, 3 newly installed, 0 to remove and 62 not upgraded.
defender: Need to get 7112 kB of archives.
defender: After this operation, 34.1 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 libblas-dev amd64 3.11.0-2 [158 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 liblapack3 amd64 3.11.0-2 [2323 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 liblapack-dev amd64 3.11.0-2 [4631 kB]
defender: Fetched 7112 kB in 2s (3798 kB/s)
defender: Selecting previously unselected package libblas-dev:amd64.
(Reading database ... 92513 files and directories currently installed.)
defender: Preparing to unpack .../libblas-dev_3.11.0-2_amd64.deb ...
defender: Unpacking libblas-dev:amd64 (3.11.0-2) ...
defender: Selecting previously unselected package liblapack3:amd64.
defender: Preparing to unpack .../liblapack3_3.11.0-2_amd64.deb ...
defender: Unpacking liblapack3:amd64 (3.11.0-2) ...
defender: Selecting previously unselected package liblapack-dev:amd64.
defender: Preparing to unpack .../liblapack-dev_3.11.0-2_amd64.deb ...
defender: Unpacking liblapack-dev:amd64 (3.11.0-2) ...
defender: Setting up liblapack3:amd64 (3.11.0-2) ...
defender: update-alternatives: using /usr/lib/x86_64-linux-gnu/lapack/liblapack.so.3 to provide /usr/lib/x86_64-linux-gnu/liblapack.so.3 (liblapack.so.3-x86_64-linux-gnu) in auto mode
defender: Setting up libblas-dev:amd64 (3.11.0-2) ...
defender: update-alternatives: using /usr/lib/x86_64-linux-gnu/blas/libblas.so to provide /usr/lib/x86_64-linux-gnu/libblas.so (libblas.so-x86_64-linux-gnu) in auto mode
defender: Setting up liblapack-dev:amd64 (3.11.0-2) ...
defender: update-alternatives: using /usr/lib/x86_64-linux-gnu/lapack/liblapack.so to provide /usr/lib/x86_64-linux-gnu/liblapack.so (liblapack.so-x86_64-linux-gnu) in auto mode
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: ++ cd /tmp
defender: ++ rm -rf faiss
defender: ++ git clone --depth 1 --branch v1.8.0 https://github.com/facebookresearch/faiss.git
defender: Cloning into 'faiss'...
defender: Note: switching to '943d08bdad7946b22f56d040756669ee444dd681'.
defender:
defender: You are in 'detached HEAD' state. You can look around, make experimental
defender: changes and commit them, and you can discard any commits you make in this
defender: state without impacting any branches by switching back to a branch.
defender:
defender: If you want to create a new branch to retain commits you create, you may
defender: do so (now or later) by using -c with the switch command. Example:
defender:
defender:   git switch -c <new-branch-name>
defender:
defender: Or undo this operation with:
defender:
defender:   git switch -
defender:
defender: Turn off this advice by setting config variable advice.detachedHead to false
defender:
defender: ++ cd faiss
defender: ++ mkdir -p build
defender: ++ cd build
defender: ++ cmake .. -DFAISS_ENABLE_GPU=OFF -DFAISS_ENABLE_PYTHON=OFF -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local
defender: -- The CXX compiler identification is GNU 12.2.0
defender: -- Detecting CXX compiler ABI info
defender: -- Detecting CXX compiler ABI info - done
defender: -- Check for working CXX compiler: /usr/bin/c++ - skipped
defender: -- Detecting CXX compile features
defender: -- Detecting CXX compile features - done
defender: -- Found OpenMP_CXX: -fopenmp (found version "4.5")
defender: -- Found OpenMP: TRUE (found version "4.5")
defender: -- Performing Test CMAKE_HAVE_LIBC_PTHREAD
defender: -- Performing Test CMAKE_HAVE_LIBC_PTHREAD - Success
defender: -- Found Threads: TRUE
defender: -- Could NOT find MKL (missing: MKL_LIBRARIES)
defender: -- Looking for sgemm_
defender: -- Looking for sgemm_ - not found
defender: -- Looking for sgemm_
defender: -- Looking for sgemm_ - found
defender: -- Found BLAS: /usr/lib/x86_64-linux-gnu/libblas.so
defender: -- Looking for cheev_
defender: -- Looking for cheev_ - not found
defender: -- Looking for cheev_
defender: -- Looking for cheev_ - found
defender: -- Found LAPACK: /usr/lib/x86_64-linux-gnu/liblapack.so;/usr/lib/x86_64-linux-gnu/libblas.so
defender: -- Configuring done
defender: -- Generating done
defender: -- Build files have been written to: /tmp/faiss/build
defender: +++ nproc
defender: ++ make -j6
defender: [  0%] Building CXX object faiss/CMakeFiles/faiss.dir/Clustering.cpp.o
defender: [  0%] Building CXX object faiss/CMakeFiles/faiss.dir/Index2Layer.cpp.o
defender: [  0%] Building CXX object faiss/CMakeFiles/faiss.dir/IVFlib.cpp.o
defender: [  3%] Building CXX object faiss/CMakeFiles/faiss.dir/AutoTune.cpp.o
defender: [  6%] Building CXX object faiss/CMakeFiles/faiss.dir/Index.cpp.o
defender: [  6%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexAdditiveQuantizer.cpp.o
defender: [  9%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexBinary.cpp.o
defender: [  9%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexBinaryFlat.cpp.o
defender: [  9%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexBinaryFromFloat.cpp.o
defender: [ 12%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexBinaryHNSW.cpp.o
defender: [ 12%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexBinaryHash.cpp.o
defender: [ 12%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexBinaryIVF.cpp.o
defender: [ 16%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexFlat.cpp.o
defender: [ 16%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexFlatCodes.cpp.o
defender: [ 16%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexHNSW.cpp.o
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/IndexBinaryHNSW.cpp:31:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/IndexBinaryHash.cpp:17:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: [ 19%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIDMap.cpp.o
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/IndexBinaryIVF.cpp:23:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: [ 19%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVF.cpp.o
defender: [ 22%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFAdditiveQuantizer.cpp.o
defender: [ 22%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFFlat.cpp.o
defender: [ 22%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFPQ.cpp.o
defender: [ 25%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFFastScan.cpp.o
defender: [ 25%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFAdditiveQuantizerFastScan.cpp.o
defender: [ 25%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFPQFastScan.cpp.o
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/IndexIVFPQ.cpp:27:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: [ 29%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFPQR.cpp.o
defender: [ 29%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFSpectralHash.cpp.o
defender: [ 29%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexLSH.cpp.o
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/IndexIVFSpectralHash.cpp:21:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: [ 32%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexNNDescent.cpp.o
defender: [ 32%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexLattice.cpp.o
defender: [ 32%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexNSG.cpp.o
defender: [ 35%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexPQ.cpp.o
defender: [ 35%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexFastScan.cpp.o
defender: [ 35%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexAdditiveQuantizerFastScan.cpp.o
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/IndexPQ.cpp:21:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: [ 38%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexIVFIndependentQuantizer.cpp.o
defender: [ 38%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexPQFastScan.cpp.o
defender: [ 38%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexPreTransform.cpp.o
defender: [ 41%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexRefine.cpp.o
defender: [ 41%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexReplicas.cpp.o
defender: [ 41%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexRowwiseMinMax.cpp.o
defender: [ 45%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexScalarQuantizer.cpp.o
defender: [ 45%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexShards.cpp.o
defender: [ 45%] Building CXX object faiss/CMakeFiles/faiss.dir/IndexShardsIVF.cpp.o
defender: [ 48%] Building CXX object faiss/CMakeFiles/faiss.dir/MatrixStats.cpp.o
defender: [ 48%] Building CXX object faiss/CMakeFiles/faiss.dir/MetaIndexes.cpp.o
defender: [ 48%] Building CXX object faiss/CMakeFiles/faiss.dir/VectorTransform.cpp.o
defender: [ 51%] Building CXX object faiss/CMakeFiles/faiss.dir/clone_index.cpp.o
defender: [ 51%] Building CXX object faiss/CMakeFiles/faiss.dir/index_factory.cpp.o
defender: [ 51%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/AuxIndexStructures.cpp.o
defender: [ 54%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/CodePacker.cpp.o
defender: [ 54%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/IDSelector.cpp.o
defender: [ 54%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/FaissException.cpp.o
defender: [ 58%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/HNSW.cpp.o
defender: [ 58%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/NSG.cpp.o
defender: [ 58%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/PolysemousTraining.cpp.o
defender: [ 61%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/ProductQuantizer.cpp.o
defender: [ 61%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/AdditiveQuantizer.cpp.o
defender: [ 61%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/ResidualQuantizer.cpp.o
defender: [ 64%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/LocalSearchQuantizer.cpp.o
defender: [ 64%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/ProductAdditiveQuantizer.cpp.o
defender: [ 67%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/ScalarQuantizer.cpp.o
defender: [ 67%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/index_read.cpp.o
defender: [ 67%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/index_write.cpp.o
defender: [ 70%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/io.cpp.o
defender: [ 70%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/kmeans1d.cpp.o
defender: [ 70%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/lattice_Zn.cpp.o
defender: [ 74%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/pq4_fast_scan.cpp.o
defender: [ 74%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/pq4_fast_scan_search_1.cpp.o
defender: [ 74%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/pq4_fast_scan_search_qbs.cpp.o
defender: [ 77%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/residual_quantizer_encode_steps.cpp.o
defender: [ 77%] Building CXX object faiss/CMakeFiles/faiss.dir/impl/NNDescent.cpp.o
defender: [ 77%] Building CXX object faiss/CMakeFiles/faiss.dir/invlists/BlockInvertedLists.cpp.o
defender: [ 80%] Building CXX object faiss/CMakeFiles/faiss.dir/invlists/DirectMap.cpp.o
defender: [ 80%] Building CXX object faiss/CMakeFiles/faiss.dir/invlists/InvertedLists.cpp.o
defender: [ 80%] Building CXX object faiss/CMakeFiles/faiss.dir/invlists/InvertedListsIOHook.cpp.o
defender: [ 83%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/Heap.cpp.o
defender: [ 83%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/WorkerThread.cpp.o
defender: [ 83%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/distances.cpp.o
defender: [ 87%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/distances_simd.cpp.o
defender: [ 87%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/extra_distances.cpp.o
defender: [ 87%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/hamming.cpp.o
defender: [ 90%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/partitioning.cpp.o
defender: In file included from /tmp/faiss/faiss/utils/hamming_distance/hamdis-inl.h:23,
defender:                  from /tmp/faiss/faiss/utils/hamming.h:34,
defender:                  from /tmp/faiss/faiss/utils/hamming.cpp:24:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h: In member function ‘int faiss::HammingComputerDefault::hamming(const uint8_t*) const’:
defender: /tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312:32: warning: statement will never be executed [-Wswitch-unreachable]
defender:   312 |                 [[fallthrough]];
defender:       |                                ^
defender: [ 90%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/quantize_lut.cpp.o
defender: [ 90%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/random.cpp.o
defender: [ 93%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/sorting.cpp.o
defender: [ 93%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/utils.cpp.o
defender: [ 93%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/distances_fused/avx512.cpp.o
defender: [ 96%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/distances_fused/distances_fused.cpp.o
defender: [ 96%] Building CXX object faiss/CMakeFiles/faiss.dir/utils/distances_fused/simdlib_based.cpp.o
defender: [ 96%] Building CXX object faiss/CMakeFiles/faiss.dir/invlists/OnDiskInvertedLists.cpp.o
defender: [100%] Linking CXX shared library libfaiss.so
defender: [100%] Built target faiss
defender: ++ make install
defender: [100%] Built target faiss
defender: Install the project...
defender: -- Install configuration: "Release"
defender: -- Installing: /usr/local/lib/libfaiss.so
defender: -- Installing: /usr/local/include/faiss/AutoTune.h
defender: -- Installing: /usr/local/include/faiss/Clustering.h
defender: -- Installing: /usr/local/include/faiss/IVFlib.h
defender: -- Installing: /usr/local/include/faiss/Index.h
defender: -- Installing: /usr/local/include/faiss/Index2Layer.h
defender: -- Installing: /usr/local/include/faiss/IndexAdditiveQuantizer.h
defender: -- Installing: /usr/local/include/faiss/IndexBinary.h
defender: -- Installing: /usr/local/include/faiss/IndexBinaryFlat.h
defender: -- Installing: /usr/local/include/faiss/IndexBinaryFromFloat.h
defender: -- Installing: /usr/local/include/faiss/IndexBinaryHNSW.h
defender: -- Installing: /usr/local/include/faiss/IndexBinaryHash.h
defender: -- Installing: /usr/local/include/faiss/IndexBinaryIVF.h
defender: -- Installing: /usr/local/include/faiss/IndexFlat.h
defender: -- Installing: /usr/local/include/faiss/IndexFlatCodes.h
defender: -- Installing: /usr/local/include/faiss/IndexHNSW.h
defender: -- Installing: /usr/local/include/faiss/IndexIDMap.h
defender: -- Installing: /usr/local/include/faiss/IndexIVF.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFAdditiveQuantizer.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFIndependentQuantizer.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFFlat.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFPQ.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFFastScan.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFAdditiveQuantizerFastScan.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFPQFastScan.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFPQR.h
defender: -- Installing: /usr/local/include/faiss/IndexIVFSpectralHash.h
defender: -- Installing: /usr/local/include/faiss/IndexLSH.h
defender: -- Installing: /usr/local/include/faiss/IndexLattice.h
defender: -- Installing: /usr/local/include/faiss/IndexNNDescent.h
defender: -- Installing: /usr/local/include/faiss/IndexNSG.h
defender: -- Installing: /usr/local/include/faiss/IndexPQ.h
defender: -- Installing: /usr/local/include/faiss/IndexFastScan.h
defender: -- Installing: /usr/local/include/faiss/IndexAdditiveQuantizerFastScan.h
defender: -- Installing: /usr/local/include/faiss/IndexPQFastScan.h
defender: -- Installing: /usr/local/include/faiss/IndexPreTransform.h
defender: -- Installing: /usr/local/include/faiss/IndexRefine.h
defender: -- Installing: /usr/local/include/faiss/IndexReplicas.h
defender: -- Installing: /usr/local/include/faiss/IndexRowwiseMinMax.h
defender: -- Installing: /usr/local/include/faiss/IndexScalarQuantizer.h
defender: -- Installing: /usr/local/include/faiss/IndexShards.h
defender: -- Installing: /usr/local/include/faiss/IndexShardsIVF.h
defender: -- Installing: /usr/local/include/faiss/MatrixStats.h
defender: -- Installing: /usr/local/include/faiss/MetaIndexes.h
defender: -- Installing: /usr/local/include/faiss/MetricType.h
defender: -- Installing: /usr/local/include/faiss/VectorTransform.h
defender: -- Installing: /usr/local/include/faiss/clone_index.h
defender: -- Installing: /usr/local/include/faiss/index_factory.h
defender: -- Installing: /usr/local/include/faiss/index_io.h
defender: -- Installing: /usr/local/include/faiss/impl/AdditiveQuantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/AuxIndexStructures.h
defender: -- Installing: /usr/local/include/faiss/impl/CodePacker.h
defender: -- Installing: /usr/local/include/faiss/impl/IDSelector.h
defender: -- Installing: /usr/local/include/faiss/impl/DistanceComputer.h
defender: -- Installing: /usr/local/include/faiss/impl/FaissAssert.h
defender: -- Installing: /usr/local/include/faiss/impl/FaissException.h
defender: -- Installing: /usr/local/include/faiss/impl/HNSW.h
defender: -- Installing: /usr/local/include/faiss/impl/LocalSearchQuantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/ProductAdditiveQuantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/LookupTableScaler.h
defender: -- Installing: /usr/local/include/faiss/impl/NNDescent.h
defender: -- Installing: /usr/local/include/faiss/impl/NSG.h
defender: -- Installing: /usr/local/include/faiss/impl/PolysemousTraining.h
defender: -- Installing: /usr/local/include/faiss/impl/ProductQuantizer-inl.h
defender: -- Installing: /usr/local/include/faiss/impl/ProductQuantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/Quantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/ResidualQuantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/ResultHandler.h
defender: -- Installing: /usr/local/include/faiss/impl/ScalarQuantizer.h
defender: -- Installing: /usr/local/include/faiss/impl/ThreadedIndex-inl.h
defender: -- Installing: /usr/local/include/faiss/impl/ThreadedIndex.h
defender: -- Installing: /usr/local/include/faiss/impl/io.h
defender: -- Installing: /usr/local/include/faiss/impl/io_macros.h
defender: -- Installing: /usr/local/include/faiss/impl/kmeans1d.h
defender: -- Installing: /usr/local/include/faiss/impl/lattice_Zn.h
defender: -- Installing: /usr/local/include/faiss/impl/platform_macros.h
defender: -- Installing: /usr/local/include/faiss/impl/pq4_fast_scan.h
defender: -- Installing: /usr/local/include/faiss/impl/residual_quantizer_encode_steps.h
defender: -- Installing: /usr/local/include/faiss/impl/simd_result_handlers.h
defender: -- Installing: /usr/local/include/faiss/impl/code_distance/code_distance.h
defender: -- Installing: /usr/local/include/faiss/impl/code_distance/code_distance-generic.h
defender: -- Installing: /usr/local/include/faiss/impl/code_distance/code_distance-avx2.h
defender: -- Installing: /usr/local/include/faiss/invlists/BlockInvertedLists.h
defender: -- Installing: /usr/local/include/faiss/invlists/DirectMap.h
defender: -- Installing: /usr/local/include/faiss/invlists/InvertedLists.h
defender: -- Installing: /usr/local/include/faiss/invlists/InvertedListsIOHook.h
defender: -- Installing: /usr/local/include/faiss/utils/AlignedTable.h
defender: -- Installing: /usr/local/include/faiss/utils/Heap.h
defender: -- Installing: /usr/local/include/faiss/utils/WorkerThread.h
defender: -- Installing: /usr/local/include/faiss/utils/distances.h
defender: -- Installing: /usr/local/include/faiss/utils/extra_distances-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/extra_distances.h
defender: -- Installing: /usr/local/include/faiss/utils/fp16-fp16c.h
defender: -- Installing: /usr/local/include/faiss/utils/fp16-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/fp16-arm.h
defender: -- Installing: /usr/local/include/faiss/utils/fp16.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming.h
defender: -- Installing: /usr/local/include/faiss/utils/ordered_key_value.h
defender: -- Installing: /usr/local/include/faiss/utils/partitioning.h
defender: -- Installing: /usr/local/include/faiss/utils/prefetch.h
defender: -- Installing: /usr/local/include/faiss/utils/quantize_lut.h
defender: -- Installing: /usr/local/include/faiss/utils/random.h
defender: -- Installing: /usr/local/include/faiss/utils/sorting.h
defender: -- Installing: /usr/local/include/faiss/utils/simdlib.h
defender: -- Installing: /usr/local/include/faiss/utils/simdlib_avx2.h
defender: -- Installing: /usr/local/include/faiss/utils/simdlib_emulated.h
defender: -- Installing: /usr/local/include/faiss/utils/simdlib_neon.h
defender: -- Installing: /usr/local/include/faiss/utils/utils.h
defender: -- Installing: /usr/local/include/faiss/utils/distances_fused/avx512.h
defender: -- Installing: /usr/local/include/faiss/utils/distances_fused/distances_fused.h
defender: -- Installing: /usr/local/include/faiss/utils/distances_fused/simdlib_based.h
defender: -- Installing: /usr/local/include/faiss/utils/approx_topk/approx_topk.h
defender: -- Installing: /usr/local/include/faiss/utils/approx_topk/avx2-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/approx_topk/generic.h
defender: -- Installing: /usr/local/include/faiss/utils/approx_topk/mode.h
defender: -- Installing: /usr/local/include/faiss/utils/approx_topk_hamming/approx_topk_hamming.h
defender: -- Installing: /usr/local/include/faiss/utils/transpose/transpose-avx2-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming_distance/common.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming_distance/generic-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming_distance/hamdis-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming_distance/neon-inl.h
defender: -- Installing: /usr/local/include/faiss/utils/hamming_distance/avx2-inl.h
defender: -- Installing: /usr/local/include/faiss/invlists/OnDiskInvertedLists.h
defender: -- Installing: /usr/local/share/faiss/faiss-config.cmake
defender: -- Installing: /usr/local/share/faiss/faiss-config-version.cmake
defender: -- Installing: /usr/local/share/faiss/faiss-targets.cmake
defender: -- Installing: /usr/local/share/faiss/faiss-targets-release.cmake
defender: ++ ldconfig
defender: ++ cd /tmp
defender: ++ rm -rf faiss
defender: ✅ FAISS installed successfully
defender: 🔍 Installing XGBoost 3.2.0...
defender: ++ echo '✅ FAISS installed successfully'
defender: ++ '[' '!' -f /usr/local/lib/libxgboost.so ']'
defender: ++ echo '🔍 Installing XGBoost 3.2.0...'
defender: ++ pip3 install xgboost==3.2.0 --break-system-packages --timeout=300
defender: Collecting xgboost==3.2.0
defender:   Downloading xgboost-3.2.0-py3-none-manylinux_2_28_x86_64.whl (131.7 MB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.7/131.7 MB 5.3 MB/s eta 0:00:00
defender: Collecting numpy
defender:   Downloading numpy-2.4.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (16.9 MB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 16.9/16.9 MB 5.8 MB/s eta 0:00:00
defender: Collecting nvidia-nccl-cu12
defender:   Downloading nvidia_nccl_cu12-2.30.4-py3-none-manylinux_2_18_x86_64.whl (300.2 MB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 300.2/300.2 MB 1.4 MB/s eta 0:00:00
defender: Collecting scipy
defender:   Downloading scipy-1.17.1-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (35.3 MB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 35.3/35.3 MB 5.0 MB/s eta 0:00:00
defender: Installing collected packages: nvidia-nccl-cu12, numpy, scipy, xgboost
defender: Successfully installed numpy-2.4.4 nvidia-nccl-cu12-2.30.4 scipy-1.17.1 xgboost-3.2.0
defender: WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv                                                                                                                                                   
defender: ++ mkdir -p /usr/local/include/xgboost
defender: ++ curl -fsSL https://raw.githubusercontent.com/dmlc/xgboost/v3.2.0/include/xgboost/c_api.h -o /usr/local/include/xgboost/c_api.h
defender: ++ curl -fsSL https://raw.githubusercontent.com/dmlc/xgboost/v3.2.0/include/xgboost/base.h -o /usr/local/include/xgboost/base.h
defender: +++ python3 -c 'import xgboost.core; print(xgboost.core.find_lib_path()[0])'
defender: ++ XGBOOST_SO=/usr/local/lib/python3.11/dist-packages/xgboost/lib/libxgboost.so
defender: ++ '[' -n /usr/local/lib/python3.11/dist-packages/xgboost/lib/libxgboost.so ']'
defender: ++ cp /usr/local/lib/python3.11/dist-packages/xgboost/lib/libxgboost.so /usr/local/lib/libxgboost.so
defender: ++ ldconfig
defender: +++ python3 -c 'import xgboost; print(xgboost.__version__)'
defender: ✅ XGBoost installed: 3.2.0
defender: ++ echo '✅ XGBoost installed: 3.2.0'
defender: ++ ln -sf /usr/local/lib/python3.11/dist-packages/xgboost.libs/libgomp-e985bcbb.so.1.0.0 /usr/local/lib/libgomp-e985bcbb.so.1.0.0
defender: ++ ldconfig
defender: ++ pip3 install pandas scikit-learn --break-system-packages --timeout=300
defender: Collecting pandas
defender:   Downloading pandas-3.0.2-cp311-cp311-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl (11.3 MB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11.3/11.3 MB 5.1 MB/s eta 0:00:00
defender: Collecting scikit-learn
defender:   Downloading scikit_learn-1.8.0-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl (9.1 MB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 9.1/9.1 MB 5.4 MB/s eta 0:00:00
defender: Requirement already satisfied: numpy>=1.26.0 in /usr/local/lib/python3.11/dist-packages (from pandas) (2.4.4)
defender: Collecting python-dateutil>=2.8.2
defender:   Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 229.9/229.9 kB 2.4 MB/s eta 0:00:00
defender: Requirement already satisfied: scipy>=1.10.0 in /usr/local/lib/python3.11/dist-packages (from scikit-learn) (1.17.1)
defender: Collecting joblib>=1.3.0
defender:   Downloading joblib-1.5.3-py3-none-any.whl (309 kB)
defender:      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 309.1/309.1 kB 4.0 MB/s eta 0:00:00
defender: Collecting threadpoolctl>=3.2.0
defender:   Downloading threadpoolctl-3.6.0-py3-none-any.whl (18 kB)
defender: Requirement already satisfied: six>=1.5 in /usr/lib/python3/dist-packages (from python-dateutil>=2.8.2->pandas) (1.16.0)
defender: Installing collected packages: threadpoolctl, python-dateutil, joblib, scikit-learn, pandas
defender: Successfully installed joblib-1.5.3 pandas-3.0.2 python-dateutil-2.9.0.post0 scikit-learn-1.8.0 threadpoolctl-3.6.0
defender: WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv                                                                                                                                                   
defender: ++ mkdir -p /usr/lib/ml-defender/plugins
defender: 🔌 Building plugin_xgboost...
defender: ++ '[' '!' -f /usr/lib/ml-defender/plugins/libplugin_xgboost.so ']'
defender: ++ echo '🔌 Building plugin_xgboost...'
defender: ++ cd /vagrant/plugins/xgboost
defender: ++ rm -rf build
defender: ++ mkdir -p build
defender: ++ cd build
defender: ++ cmake -DCMAKE_BUILD_TYPE=Release ..
defender: -- The CXX compiler identification is GNU 12.2.0
defender: -- The C compiler identification is GNU 12.2.0
defender: -- Detecting CXX compiler ABI info
defender: -- Detecting CXX compiler ABI info - done
defender: -- Check for working CXX compiler: /usr/bin/c++ - skipped
defender: -- Detecting CXX compile features
defender: -- Detecting CXX compile features - done
defender: -- Detecting C compiler ABI info
defender: -- Detecting C compiler ABI info - done
defender: -- Check for working C compiler: /usr/bin/cc - skipped
defender: -- Detecting C compile features
defender: -- Detecting C compile features - done
defender: -- plugin_xgboost: XGBoost headers: /usr/local/include
defender: -- plugin_xgboost: XGBoost library: /usr/local/lib/libxgboost.so
defender: -- plugin_xgboost: will build libplugin_xgboost.so (PRODUCTION — ADR-026 Track 1)
defender: -- Configuring done
defender: -- Generating done
defender: -- Build files have been written to: /vagrant/plugins/xgboost/build
defender: ++ make -j4
defender: [ 50%] Building CXX object CMakeFiles/plugin_xgboost.dir/xgboost_plugin.cpp.o
defender: [100%] Linking CXX shared library libplugin_xgboost.so
defender: [100%] Built target plugin_xgboost
defender: ++ cp libplugin_xgboost.so /usr/lib/ml-defender/plugins/
defender: ✅ plugin_xgboost deployed
defender: ++ echo '✅ plugin_xgboost deployed'
defender: ++ '[' '!' -f /usr/local/lib/libetcd-cpp-api.so ']'
defender: ++ '[' '!' -f /usr/local/lib/libetcd-cpp-api.a ']'
defender: ++ cd /tmp
defender: ++ rm -rf etcd-cpp-apiv3
defender: ++ git clone https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git
defender: Cloning into 'etcd-cpp-apiv3'...
defender: ++ cd etcd-cpp-apiv3
defender: ++ git checkout v0.15.3
defender: Note: switching to 'v0.15.3'.
defender:
defender: You are in 'detached HEAD' state. You can look around, make experimental
defender: changes and commit them, and you can discard any commits you make in this
defender: state without impacting any branches by switching back to a branch.
defender:
defender: If you want to create a new branch to retain commits you create, you may
defender: do so (now or later) by using -c with the switch command. Example:
defender:
defender:   git switch -c <new-branch-name>
defender:
defender: Or undo this operation with:
defender:
defender:   git switch -
defender:
defender: Turn off this advice by setting config variable advice.detachedHead to false
defender:
defender: HEAD is now at e31ac4d Bump up etcd-cpp-apiv3 to v0.15.3
defender: ++ mkdir build
defender: ++ cd build
defender: ++ cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=/usr/local
defender: -- The C compiler identification is GNU 12.2.0
defender: -- The CXX compiler identification is GNU 12.2.0
defender: -- Detecting C compiler ABI info
defender: -- Detecting C compiler ABI info - done
defender: -- Check for working C compiler: /usr/bin/cc - skipped
defender: -- Detecting C compile features
defender: -- Detecting C compile features - done
defender: -- Detecting CXX compiler ABI info
defender: -- Detecting CXX compiler ABI info - done
defender: -- Check for working CXX compiler: /usr/bin/c++ - skipped
defender: -- Detecting CXX compile features
defender: -- Detecting CXX compile features - done
defender: -- Building etcd-cpp-apiv3 with C++11
defender: -- Found OpenSSL: /usr/lib/x86_64-linux-gnu/libcrypto.so (found version "3.0.19")
defender: -- Found Protobuf: /usr/lib/x86_64-linux-gnu/libprotobuf.so (found version "3.21.12")
defender: -- Found ZLIB: /usr/lib/x86_64-linux-gnu/libz.so (found version "1.2.13")
defender: -- Could NOT find c-ares (missing: c-ares_DIR)
defender: -- Found c-ares: /usr/include (found version "1.18.1")
defender: -- Found Threads: TRUE
defender: -- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
defender: -- Found RE2 via pkg-config.
defender: -- Found GRPC: gRPC::gpr;gRPC::grpc;gRPC::grpc++, /usr/bin/grpc_cpp_plugin (found version: "1.51.1")
defender: -- Performing Test W_NO_CPP17_EXTENSIONS
defender: -- Performing Test W_NO_CPP17_EXTENSIONS - Success
defender: -- Configuring done
defender: -- Generating done
defender: -- Build files have been written to: /tmp/etcd-cpp-apiv3/build
defender: ++ make -j4
defender: [ 10%] Running cpp protocol buffer compiler on etcdserver.proto
defender: [ 10%] Running cpp protocol buffer compiler on google/api/annotations.proto
defender: [ 10%] Running cpp protocol buffer compiler on auth.proto
defender: [ 10%] Running cpp protocol buffer compiler on gogoproto/gogo.proto
defender: [ 16%] Running cpp protocol buffer compiler on google/api/http.proto
defender: [ 16%] Running cpp protocol buffer compiler on kv.proto
defender: [ 18%] Running cpp protocol buffer compiler on rpc.proto
defender: [ 21%] Running cpp protocol buffer compiler on v3election.proto
defender: [ 24%] Running cpp protocol buffer compiler on v3lock.proto
defender: [ 27%] Running C++ gRPC compiler on /tmp/etcd-cpp-apiv3/proto/rpc.proto
defender: [ 29%] Running C++ gRPC compiler on /tmp/etcd-cpp-apiv3/proto/v3election.proto
defender: [ 32%] Running C++ gRPC compiler on /tmp/etcd-cpp-apiv3/proto/v3lock.proto
defender: [ 32%] Built target protobuf_generates
defender: [ 37%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/KeepAlive.cpp.o
defender: [ 37%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/Response.cpp.o
defender: [ 40%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/Value.cpp.o
defender: [ 43%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/SyncClient.cpp.o
defender: [ 45%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/Watcher.cpp.o
defender: [ 48%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/v3/Action.cpp.o
defender: [ 51%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/v3/AsyncGRPC.cpp.o
defender: [ 54%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/v3/KeyValue.cpp.o
defender: [ 56%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/v3/Transaction.cpp.o
defender: [ 59%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/v3/V3Response.cpp.o
defender: [ 62%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/v3/action_constants.cpp.o
defender: [ 64%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/auth.pb.cc.o
defender: [ 67%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/etcdserver.pb.cc.o
defender: [ 70%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/gogoproto/gogo.pb.cc.o
defender: [ 72%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/google/api/annotations.pb.cc.o
defender: [ 75%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/google/api/http.pb.cc.o
defender: [ 78%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/kv.pb.cc.o
defender: [ 81%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/rpc.pb.cc.o
defender: [ 83%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/v3election.pb.cc.o
defender: [ 86%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/v3lock.pb.cc.o
defender: [ 89%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/rpc.grpc.pb.cc.o
defender: [ 91%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/v3election.grpc.pb.cc.o
defender: [ 94%] Building CXX object src/CMakeFiles/etcd-cpp-api-core-objects.dir/__/proto/gen/proto/v3lock.grpc.pb.cc.o
defender: [ 94%] Built target etcd-cpp-api-core-objects
defender: [ 97%] Building CXX object src/CMakeFiles/etcd-cpp-api.dir/Client.cpp.o
defender: [100%] Linking CXX shared library libetcd-cpp-api.so
defender: [100%] Built target etcd-cpp-api
defender: ++ make install
defender: [ 32%] Built target protobuf_generates
defender: [ 94%] Built target etcd-cpp-api-core-objects
defender: [100%] Built target etcd-cpp-api
defender: Install the project...
defender: -- Install configuration: "Release"
defender: -- Installing: /usr/local/include/etcd/KeepAlive.hpp
defender: -- Installing: /usr/local/include/etcd/SyncClient.hpp
defender: -- Installing: /usr/local/include/etcd/Response.hpp
defender: -- Installing: /usr/local/include/etcd/Value.hpp
defender: -- Installing: /usr/local/include/etcd/Watcher.hpp
defender: -- Installing: /usr/local/include/etcd/Client.hpp
defender: -- Installing: /usr/local/include/etcd/v3/action_constants.hpp
defender: -- Installing: /usr/local/include/etcd/v3/Transaction.hpp
defender: -- Installing: /usr/local/lib/cmake/etcd-cpp-api/FindGRPC.cmake
defender: -- Installing: /usr/local/lib/cmake/etcd-cpp-api/etcd-cpp-api-config.cmake
defender: -- Installing: /usr/local/lib/cmake/etcd-cpp-api/etcd-cpp-api-config-version.cmake
defender: -- Installing: /usr/local/lib/cmake/etcd-cpp-api/etcd-targets.cmake
defender: -- Installing: /usr/local/lib/cmake/etcd-cpp-api/etcd-targets-release.cmake
defender: -- Installing: /usr/local/lib/libetcd-cpp-api.so
defender: -- Set runtime path of "/usr/local/lib/libetcd-cpp-api.so" to "/usr/local/lib:/usr/local/lib64:/usr/local/lib/x86_64-linux-gnu"
defender: ++ ldconfig
defender: ++ '[' '!' -f /usr/local/include/httplib.h ']'
defender: ++ cd /tmp
defender: ++ rm -rf cpp-httplib
defender: ++ git clone https://github.com/yhirose/cpp-httplib.git
defender: Cloning into 'cpp-httplib'...
defender: ++ mkdir -p /usr/local/include
defender: ++ cp cpp-httplib/httplib.h /usr/local/include/
defender: ++ '[' '!' -f /usr/include/cryptopp/cryptlib.h ']'
defender: ++ '[' '!' -f /usr/local/include/cryptopp/cryptlib.h ']'
defender: ++ apt-get install -y libcrypto++-dev libcrypto++-doc libcrypto++-utils
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   libcrypto++8
defender: The following NEW packages will be installed:
defender:   libcrypto++-dev libcrypto++-doc libcrypto++-utils libcrypto++8
defender: 0 upgraded, 4 newly installed, 0 to remove and 62 not upgraded.
defender: Need to get 15.8 MB of archives.
defender: After this operation, 130 MB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 libcrypto++8 amd64 8.7.0+git220824-1 [1150 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libcrypto++-dev amd64 8.7.0+git220824-1 [1825 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 libcrypto++-doc all 8.7.0+git220824-1 [5113 kB]
defender: Get:4 https://deb.debian.org/debian bookworm/main amd64 libcrypto++-utils amd64 8.7.0+git220824-1 [7750 kB]
defender: Fetched 15.8 MB in 3s (4708 kB/s)
defender: Selecting previously unselected package libcrypto++8:amd64.
(Reading database ... 92537 files and directories currently installed.)
defender: Preparing to unpack .../libcrypto++8_8.7.0+git220824-1_amd64.deb ...
defender: Unpacking libcrypto++8:amd64 (8.7.0+git220824-1) ...
defender: Selecting previously unselected package libcrypto++-dev:amd64.
defender: Preparing to unpack .../libcrypto++-dev_8.7.0+git220824-1_amd64.deb ...
defender: Unpacking libcrypto++-dev:amd64 (8.7.0+git220824-1) ...
defender: Selecting previously unselected package libcrypto++-doc.
defender: Preparing to unpack .../libcrypto++-doc_8.7.0+git220824-1_all.deb ...
defender: Unpacking libcrypto++-doc (8.7.0+git220824-1) ...
defender: Selecting previously unselected package libcrypto++-utils.
defender: Preparing to unpack .../libcrypto++-utils_8.7.0+git220824-1_amd64.deb ...
defender: Unpacking libcrypto++-utils (8.7.0+git220824-1) ...
defender: Setting up libcrypto++8:amd64 (8.7.0+git220824-1) ...
defender: Setting up libcrypto++-doc (8.7.0+git220824-1) ...
defender: Setting up libcrypto++-utils (8.7.0+git220824-1) ...
defender: Setting up libcrypto++-dev:amd64 (8.7.0+git220824-1) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: ++ '[' '!' -f /vagrant/third_party/llama.cpp/build/src/libllama.a ']'
defender: ++ mkdir -p /vagrant/rag/models
defender: ++ cd /vagrant/rag/models
defender: ++ '[' '!' -f tinyllama-1.1b-chat-v1.0.Q4_0.gguf ']'
defender: ++ mkdir -p /etc/sudoers.d
defender: ++ cat
defender: ++ chmod 0440 /etc/sudoers.d/ml-defender
defender: ++ sed -i '/es_ES.UTF-8/s/^# //g' /etc/locale.gen
defender: ++ locale-gen es_ES.UTF-8
defender: Generating locales (this might take a while)...
defender:   es_ES.UTF-8... done
defender: Generation complete.
defender: ++ update-locale LANG=es_ES.UTF-8 LC_ALL=es_ES.UTF-8
defender: ++ '[' -f /proc/sys/net/core/bpf_jit_enable ']'
defender: ++ echo 1
defender: ++ mountpoint -q /sys/fs/bpf
defender: ++ grep -q /sys/fs/bpf /etc/fstab
defender: ++ echo 'none /sys/fs/bpf bpf defaults 0 0'
defender: ++ mkdir -p /vagrant/ml-detector/models/production/level1 /vagrant/ml-detector/models/production/level2 /vagrant/ml-detector/models/production/level3
defender: ++ mkdir -p /vagrant/ml-training/outputs/onnx
defender: ++ mkdir -p /vagrant/firewall-acl-agent/build/logs
defender: ++ mkdir -p /vagrant/rag/build/logs
defender: ++ mkdir -p /vagrant/logs/lab
defender: ++ mkdir -p /var/log/ml-defender
defender: ++ chown -R vagrant:vagrant /var/log/ml-defender
defender: ++ chmod 755 /var/log/ml-defender
defender: ++ '[' -f /vagrant/protobuf/generate.sh ']'
defender: ++ '[' '!' -f /vagrant/protobuf/network_security.pb.cc ']'
defender: ++ '[' -f /vagrant/protobuf/network_security.pb.cc ']'
defender: ++ mkdir -p /vagrant/firewall-acl-agent/proto
defender: ++ cp /vagrant/protobuf/network_security.pb.cc /vagrant/firewall-acl-agent/proto/
defender: ++ cp /vagrant/protobuf/network_security.pb.h /vagrant/firewall-acl-agent/proto/
defender: ++ '[' '!' -f /vagrant/firewall-acl-agent/build/firewall-acl-agent ']'
defender: ++ mkdir -p /vagrant/firewall-acl-agent/build
defender: ++ cd /vagrant/firewall-acl-agent/build
defender: ++ cmake ..
defender: -- Build type:
defender: -- C++ Standard: 20
defender: -- CXX Flags (from Makefile):
defender: -- ⚠️  backtrace library not found - using execinfo.h fallback
defender: -- ✅ Found crypto-transport: /usr/local/lib/libcrypto_transport.so
defender: -- ✅ Found seed-client: /usr/local/lib/libseed_client.so
defender: -- ✅ LZ4 found: 1.9.4
defender: -- ✅ Found etcd-client library: /vagrant/etcd-client/build/libetcd_client.so
defender: -- ✅ Protobuf unificado encontrado: /vagrant/firewall-acl-agent/build/proto/network_security.pb.cc
defender: -- ✅ Linking etcd-client library to firewall_core
defender: CMake Warning at CMakeLists.txt:282 (message):
defender:   plugin-loader not found — PLUGIN_LOADER_ENABLED disabled
defender:
defender:
defender: -- ✅ Unit tests enabled (including logger tests)
defender: --
defender: -- ╔════════════════════════════════════════════════════════╗
defender: -- ║  ML Defender - Firewall ACL Agent Configuration       ║
defender: -- ║  Day 50: Comprehensive Observability Integration      ║
defender: -- ╚════════════════════════════════════════════════════════╝
defender: --
defender: -- Version:           1.0.0
defender: -- C++ Standard:      C++20
defender: -- Build Type:
defender: -- CXX Flags:
defender: --
defender: -- ✅ Components:
defender: --   Logger:          IMPLEMENTED (async + payload storage)
defender: --   Observability:   IMPLEMENTED (Day 50 - microsecond logging)
defender: --   Crash Diag:      IMPLEMENTED (backtrace + state dumps)
defender: --   Metrics:         TODO (unified system)
defender: --   ACL Intelligence: TODO (Phase 2+)
defender: --
defender: -- 🔬 Day 50 Observability:
defender: --   Headers:         firewall_observability_logger.hpp
defender: --                    crash_diagnostics.hpp
defender: --   Log Levels:      DEBUG, INFO, BATCH, IPSET, WARN, ERROR, CRASH
defender: --   Precision:       Microsecond timestamps
defender: --   Thread Safety:   Mutex-protected + atomic counters
defender: --   Crash Handling:  Signal handlers with backtrace
defender: --   Backtrace Lib:   FALSE
defender: --
defender: -- 📊 Logging Output:
defender: --   Observability:   /vagrant/logs/firewall-acl-agent/firewall_detailed.log
defender: --   JSON metadata:   /vagrant/logs/blocked/TIMESTAMP.json
defender: --   Protobuf payload: /vagrant/logs/blocked/TIMESTAMP.proto
defender: --   Format:          Timestamp-based (unique, sortable)
defender: --
defender: -- 🔗 RAG Integration Ready:
defender: --   ✅ Structured JSON for vector DB
defender: --   ✅ Full protobuf for forensic analysis
defender: --   ✅ Async design (non-blocking)
defender: --
defender: -- 🎯 Single Source of Truth:
defender: --   Compiler Flags: Controlled by root Makefile via PROFILE
defender: --
defender: -- ⚡ Performance Target: 1M+ packets/sec DROP rate
defender: -- 🎯 Design Philosophy: Via Appia Quality
defender: -- 🔬 Day 50 Motto: Fiat Lux - Let there be light
defender: --
defender: -- ╚════════════════════════════════════════════════════════╝
defender: --
defender: -- Configuring done
defender: -- Generating done
defender: -- Build files have been written to: /vagrant/firewall-acl-agent/build
defender: ++ make -j4
defender: [  6%] Building CXX object CMakeFiles/firewall_core.dir/src/api/zmq_subscriber.cpp.o
defender: In file included from /vagrant/firewall-acl-agent/src/api/zmq_subscriber.cpp:7:
defender: /vagrant/firewall-acl-agent/include/firewall/zmq_subscriber.hpp:54:10: fatal error: seed_client/seed_client.hpp: No such file or directory
defender:    54 | #include <seed_client/seed_client.hpp>
defender:       |          ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~
defender: compilation terminated.
defender: make[2]: *** [CMakeFiles/firewall_core.dir/build.make:146: CMakeFiles/firewall_core.dir/src/api/zmq_subscriber.cpp.o] Error 1
defender: make[1]: *** [CMakeFiles/Makefile2:87: CMakeFiles/firewall_core.dir/all] Error 2
defender: make: *** [Makefile:146: all] Error 2
defender: ++ grep -q 'FAISS Ingestion aliases' /home/vagrant/.bashrc
defender: ++ cat
defender: ✅ PROVISIONING COMPLETED SUCCESSFULLY!
defender: ++ echo '✅ PROVISIONING COMPLETED SUCCESSFULLY!'
defender: ++ mkdir -p /vagrant/dist/vendor
defender: ++ ls /vagrant/dist/vendor/falco_0.43.1_amd64.deb
defender: ✅ Falco .deb ya presente en /vagrant/dist/vendor/
defender: ++ echo '✅ Falco .deb ya presente en /vagrant/dist/vendor/'
defender: ++ sha256sum /vagrant/dist/vendor/falco_0.43.1_amd64.deb
defender: ✅ dist/vendor/CHECKSUMS actualizado
defender: ++ echo '✅ dist/vendor/CHECKSUMS actualizado'
==> defender: Running provisioner: configure-sniffer (shell)...
defender: Running: script: configure-sniffer
defender: 🔧 Auto-configuring sniffer.json for current network topology...
defender: ✅ Gateway interface detected: eth2
defender: ✅ sniffer.json updated with gateway interface: eth2
defender: ═══════════════════════════════════════════════════════════
defender: 🎯 SNIFFER AUTO-CONFIGURATION COMPLETE
defender: ═══════════════════════════════════════════════════════════
defender: WAN interface:     eth1 (192.168.56.20)
defender: Gateway interface: eth2 (192.168.100.1)
defender: ═══════════════════════════════════════════════════════════
==> defender: Running provisioner: configure-cron-restart (shell)...
defender: Running: script: configure-cron-restart
defender: ⏰ Configurando cron para restart automático cada 72h...
defender: ✅ Cron configurado: Restart cada 3 días a las 3:00 AM
defender: # ML Defender restart every 72h (memory leak mitigation)
defender: 0 3 */3 * * /vagrant/scripts/restart_ml_defender.sh
==> defender: Running provisioner: configure-sqlite-day40 (shell)...
defender: Running: script: configure-sqlite-day40
defender: 📁 Day 40: Creating shared indices directory...
defender: ✅ Shared indices directory ready: /vagrant/shared/indices
defender: 📦 Installing SQLite3 development headers + CLI...
defender: Reading package lists...
defender: Building dependency tree...
defender: Reading state information...
defender: The following additional packages will be installed:
defender:   libsqlite3-0
defender: Suggested packages:
defender:   sqlite3-doc
defender: The following NEW packages will be installed:
defender:   libsqlite3-dev sqlite3
defender: The following packages will be upgraded:
defender:   libsqlite3-0
defender: 1 upgraded, 2 newly installed, 0 to remove and 61 not upgraded.
defender: Need to get 2217 kB of archives.
defender: After this operation, 3771 kB of additional disk space will be used.
defender: Get:1 https://deb.debian.org/debian bookworm/main amd64 libsqlite3-0 amd64 3.40.1-2+deb12u2 [839 kB]
defender: Get:2 https://deb.debian.org/debian bookworm/main amd64 libsqlite3-dev amd64 3.40.1-2+deb12u2 [1025 kB]
defender: Get:3 https://deb.debian.org/debian bookworm/main amd64 sqlite3 amd64 3.40.1-2+deb12u2 [353 kB]
defender: apt-listchanges: Reading changelogs...
defender: dpkg-preconfigure: unable to re-open stdin: No such file or directory
defender: Fetched 2217 kB in 1s (3162 kB/s)
(Reading database ... 96192 files and directories currently installed.)
defender: Preparing to unpack .../libsqlite3-0_3.40.1-2+deb12u2_amd64.deb ...
defender: Unpacking libsqlite3-0:amd64 (3.40.1-2+deb12u2) over (3.40.1-2) ...
defender: Selecting previously unselected package libsqlite3-dev:amd64.
defender: Preparing to unpack .../libsqlite3-dev_3.40.1-2+deb12u2_amd64.deb ...
defender: Unpacking libsqlite3-dev:amd64 (3.40.1-2+deb12u2) ...
defender: Selecting previously unselected package sqlite3.
defender: Preparing to unpack .../sqlite3_3.40.1-2+deb12u2_amd64.deb ...
defender: Unpacking sqlite3 (3.40.1-2+deb12u2) ...
defender: Setting up libsqlite3-0:amd64 (3.40.1-2+deb12u2) ...
defender: Setting up libsqlite3-dev:amd64 (3.40.1-2+deb12u2) ...
defender: Setting up sqlite3 (3.40.1-2+deb12u2) ...
defender: Processing triggers for man-db (2.11.2-2) ...
defender: Processing triggers for libc-bin (2.36-9+deb12u13) ...
defender: ✅ SQLite3 dev + CLI installed
==> defender: Running provisioner: cryptographic-provisioning (shell)...
defender: Running: script: cryptographic-provisioning
defender: ╔════════════════════════════════════════════════════════════╗
defender: ║  🔐 Cryptographic Provisioning (DAY 95 — PHASE 1)         ║
defender: ╚════════════════════════════════════════════════════════════╝
defender:
defender: ╔══════════════════════════════════════════════════════════════╗
defender: ║  ML Defender — Provisioning Criptográfico PHASE 1            ║
defender: ╚══════════════════════════════════════════════════════════════╝
defender:
defender:   Keys root:  /etc/ml-defender/
defender:   Algorithm:  Ed25519 keypairs + ChaCha20 seeds (32B)
defender:   libsodium:  1.0.19 (HKDF nativo, ADR-013)
defender:   AppArmor:   Compatible (paths fijos, ADR-019)
defender:
defender:
defender: ══ Verificación de entropía del sistema ══
defender:      → Entropía disponible: 256 bits
defender:   ✅ Entropía suficiente (256 bits) — no se requiere haveged
defender:
defender: ══ libsodium 1.0.19 ══
defender:   ✅ libsodium 1.0.19 ya instalada con HKDF nativo — saltando
defender:
defender: ══ Shared libs (seed-client + crypto-transport + plugin-loader) ══
defender:      → Compilando seed-client...
defender:      → seed-client instalada en /usr/local
defender:      → Compilando crypto-transport...
defender:      → crypto-transport instalada en /usr/local
defender:      → Generando plugin signing keypair (requerido por plugin-loader cmake)...
defender:
defender: ══ Plugin Signing Keypair (ADR-025) ══
defender:      → Plugin signing keypair generado
defender:      → Private key: /etc/ml-defender/plugins/plugin_signing.sk (0600 -- NUNCA fuera de este host)
defender:      → Public key:  /etc/ml-defender/plugins/plugin_signing.pk (0644)
defender:      →
defender:      → >>> MLD_PLUGIN_PUBKEY_HEX=388cd5771301ee069ab2e5e60a3809ec34fc5dacb9f6ca1d6421987ef8cc5e6b <<<
defender:      →     Hardcodear en plugin-loader/CMakeLists.txt (ADR-025 D7)
defender:      →     Esta es la UNICA vez que se muestra en provision.sh
defender:      → Compilando plugin-loader...
defender:      → plugin-loader instalada en /usr/local
defender:      → Instalando libsnappy...
defender:      → libsnappy instalada
defender:      → Instalando etcd-client...
defender:      → etcd-client instalada en /usr/local
defender:   ✅ Shared libs OK
defender:
defender: ══ Componentes del pipeline (6) ══
defender:
defender:   etcd-server
defender:      → Directorio creado: /etc/ml-defender/etcd-server
defender:      → Keypair Ed25519 generado para etcd-server
defender:      → Seed ChaCha20 (32B) generado para etcd-server
defender:   ✅ etcd-server provisionado correctamente
defender:
defender:   sniffer
defender:      → Directorio creado: /etc/ml-defender/sniffer
defender:      → Keypair Ed25519 generado para sniffer
defender:      → Seed ChaCha20 (32B) generado para sniffer
defender:   ✅ sniffer provisionado correctamente
defender:
defender:   ml-detector
defender:      → Directorio creado: /etc/ml-defender/ml-detector
defender:      → Keypair Ed25519 generado para ml-detector
defender:      → Seed ChaCha20 (32B) generado para ml-detector
defender:   ✅ ml-detector provisionado correctamente
defender:
defender:   firewall-acl-agent
defender:      → Directorio creado: /etc/ml-defender/firewall-acl-agent
defender:      → Keypair Ed25519 generado para firewall-acl-agent
defender:      → Seed ChaCha20 (32B) generado para firewall-acl-agent
defender:   ✅ firewall-acl-agent provisionado correctamente
defender:
defender:   rag-ingester
defender:      → Directorio creado: /etc/ml-defender/rag-ingester
defender:      → Keypair Ed25519 generado para rag-ingester
defender:      → Seed ChaCha20 (32B) generado para rag-ingester
defender:   ✅ rag-ingester provisionado correctamente
defender:
defender:   rag-security
defender:      → Directorio creado: /etc/ml-defender/rag-security
defender:      → Keypair Ed25519 generado para rag-security
defender:      → Seed ChaCha20 (32B) generado para rag-security
defender:   ✅ rag-security provisionado correctamente
defender:
defender: ══ Plugins Userspace (ADR-017) ══
defender:      → No hay plugins declarados en los JSONs (PHASE 2 pendiente)
defender:      → Directorio /etc/ml-defender/plugins/ creado y listo
defender:
defender: ══ Plugins eBPF (ADR-018) ══
defender:      → kernel_telemetry.json no encontrado (ADR-018 pendiente)
defender:      → Directorio /etc/ml-defender/ebpf-plugins/ creado y listo
defender:
defender: ══ Plugin Signing Keypair (ADR-025) ══
defender:   ⚠️  Plugin signing keypair ya existe -- skip (usa --reset para rotar)
defender:      → Public key hex (MLD_PLUGIN_PUBKEY_HEX): 388cd5771301ee069ab2e5e60a3809ec34fc5dacb9f6ca1d6421987ef8cc5e6b
defender:
defender: ══ Sincronización de seed maestro (etcd-server → 5 componentes) ══
defender:      → Seed sincronizado → sniffer
defender:      → Seed sincronizado → ml-detector
defender:      → Seed sincronizado → firewall-acl-agent
defender:      → Seed sincronizado → rag-ingester
defender:      → Seed sincronizado → rag-security
defender:   ✅ Seeds sincronizados (todos los componentes usan el seed de etcd-server)
defender:
defender: ══ Symlinks JSON config (6 componentes) ══
defender:      → Symlink: /etc/ml-defender/etcd-server/etcd-server.json → /vagrant/etcd-server/config/etcd-server.json
defender:      → Symlink: /etc/ml-defender/sniffer/sniffer-libpcap.json → /vagrant/sniffer/config/sniffer-libpcap.json
defender:      → Symlink: /etc/ml-defender/sniffer/sniffer.json → /vagrant/sniffer/config/sniffer.json
defender:      → Symlink: /etc/ml-defender/ml-detector/feature_mapping.json → /vagrant/ml-detector/config/feature_mapping.json
defender:      → Symlink: /etc/ml-defender/ml-detector/ml_detector_config.json → /vagrant/ml-detector/config/ml_detector_config.json
defender:      → Symlink: /etc/ml-defender/ml-detector/rag_logger_config.json → /vagrant/ml-detector/config/rag_logger_config.json
defender:      → Symlink: /etc/ml-defender/firewall-acl-agent/firewall.json → /vagrant/firewall-acl-agent/config/firewall.json
defender:      → Symlink: /etc/ml-defender/rag-ingester/rag-ingester-test.json → /vagrant/rag-ingester/config/rag-ingester-test.json
defender:      → Symlink: /etc/ml-defender/rag-ingester/rag-ingester.json → /vagrant/rag-ingester/config/rag-ingester.json
defender:
defender: ══ libsodium compat symlink (so.23 → so.26) ══
defender:      → Symlink creado: /usr/local/lib/libsodium.so.23 → libsodium.so.26
defender:      → ldconfig ejecutado
defender:
defender: ══ libcrypto_transport.so — verificación de fecha ══
defender:   ✅ libcrypto_transport.so actualizada (2026-05-06)
defender:
defender: ══ argus-network-isolate — ADR-042 IRP config ══
defender:      → isolate.json instalado en /etc/ml-defender/firewall-acl-agent/isolate.json
defender:      → /var/log/argus/ listo (forense ADR-042)
defender:
defender: ══ Verificación post-provisioning ══
defender:
defender: ══ Verificación de integridad ══
defender:   ✅ etcd-server: OK
defender:   ✅ sniffer: OK
defender:   ✅ ml-detector: OK
defender:   ✅ firewall-acl-agent: OK
defender:   ✅ rag-ingester: OK
defender:   ✅ rag-security: OK
defender:
defender:   ✅ Todas las claves verificadas correctamente
defender:
defender: ╔══════════════════════════════════════════════════════════════╗
defender: ║  ✅ PROVISIONING COMPLETADO CORRECTAMENTE                    ║
defender: ╚══════════════════════════════════════════════════════════════╝
defender:
defender:   libsodium:     1.0.19 con HKDF nativo
defender:   Siguiente:     make pipeline-start
defender:   Verificar:     make provision-status
defender:
defender: ✅ Cryptographic provisioning completed
defender:    Keys at: /etc/ml-defender/
defender:    Verify:  sudo bash /vagrant/tools/provision.sh status
defender: 📦 Installing systemd units (TEST-PROVISION-1 Check 5)...
defender: ═══ Instalando systemd units ML Defender (PHASE 3) ═══
defender:   ✅ Instalado: /etc/systemd/system/ml-defender-etcd-server.service
defender:   ✅ Instalado: /etc/systemd/system/ml-defender-rag-security.service
defender:   ✅ Instalado: /etc/systemd/system/ml-defender-rag-ingester.service
defender:   ✅ Instalado: /etc/systemd/system/ml-defender-ml-detector.service
defender:   ✅ Instalado: /etc/systemd/system/ml-defender-sniffer.service
defender:   ✅ Instalado: /etc/systemd/system/ml-defender-firewall-acl-agent.service
defender:
defender: ⏳ Recargando systemd daemon...
defender:
defender: ⚠️  Units instalados pero NO habilitados ni iniciados.
defender:    Para habilitar en arranque:
defender:      systemctl enable ml-defender-etcd-server.service
defender:      systemctl enable ml-defender-rag-security.service
defender:      systemctl enable ml-defender-rag-ingester.service
defender:      systemctl enable ml-defender-ml-detector.service
defender:      systemctl enable ml-defender-sniffer.service
defender:      systemctl enable ml-defender-firewall-acl-agent.service
defender:
defender:    Para verificar:
defender:      systemctl status ml-defender-*.service
defender:
defender: ═══ Instalación completada ═══
defender: ✅ systemd units installed

==> defender: Machine 'defender' has a post `vagrant up` message. This is a message
==> defender: from the creator of the Vagrantfile, and not from Vagrant itself:                                                                                                                
==> defender:                                                                                                                                                                                  
==> defender: Vanilla Debian box. See https://app.vagrantup.com/debian for help and bug reports                                                                                                
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker %
## make bootstrap
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % make bootstrap
╔════════════════════════════════════════════════════════════╗
║  🚀 aRGus NDR — Bootstrap from scratch                    ║
║  Ejecutar tras: git clone && make up                      ║
╚════════════════════════════════════════════════════════════╝
[1/8] Verificando entorno post-up...
🔍 Verificando entorno post-up...
🔍 Verificando dependencias del sistema...
✅ Todas las dependencias del sistema presentes
✅ Entorno post-up verificado
[2/8] Verificando dependencias del sistema...
🔍 Verificando dependencias del sistema...
✅ Todas las dependencias del sistema presentes
[3/8] Activando perfil de build...
═══ Activando perfil de build: debug ═══
═══ Activando perfil: debug ═══
✅ etcd-server: build-active → build-debug
✅ rag: build-active → build-debug
✅ rag-ingester: build-active → build-debug
✅ ml-detector: build-active → build-debug
✅ sniffer: build-active → build-debug
✅ firewall-acl-agent: build-active → build-debug

Perfil activo guardado en /etc/ml-defender/build.env
Recarga units: sudo systemctl daemon-reload
═══ Listo ═══
[4/8] Instalando systemd units...
═══ Instalando systemd units ML Defender ═══
═══ Instalando systemd units ML Defender (PHASE 3) ═══
✅ Instalado: /etc/systemd/system/ml-defender-etcd-server.service
✅ Instalado: /etc/systemd/system/ml-defender-rag-security.service
✅ Instalado: /etc/systemd/system/ml-defender-rag-ingester.service
✅ Instalado: /etc/systemd/system/ml-defender-ml-detector.service
✅ Instalado: /etc/systemd/system/ml-defender-sniffer.service
✅ Instalado: /etc/systemd/system/ml-defender-firewall-acl-agent.service

⏳ Recargando systemd daemon...

⚠️  Units instalados pero NO habilitados ni iniciados.
Para habilitar en arranque:
systemctl enable ml-defender-etcd-server.service
systemctl enable ml-defender-rag-security.service
systemctl enable ml-defender-rag-ingester.service
systemctl enable ml-defender-ml-detector.service
systemctl enable ml-defender-sniffer.service
systemctl enable ml-defender-firewall-acl-agent.service

Para verificar:
systemctl status ml-defender-*.service

═══ Instalación completada ═══
[5/8] Compilando pipeline (incluye pubkey runtime + plugin-test-message)...
╔══════════════════════════════════════════════╗
║  Building seed-client...                     ║
╚══════════════════════════════════════════════╝
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Found nlohmann_json: /usr/share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake (found suitable version "3.11.2", minimum required is "3.9")
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/libs/seed-client/build
[ 12%] Building CXX object CMakeFiles/seed_client.dir/src/seed_client.cpp.o
[ 25%] Linking CXX shared library libseed_client.so
[ 25%] Built target seed_client
[ 62%] Building CXX object CMakeFiles/test_seed_client_traversal.dir/tests/test_seed_client_traversal.cpp.o
[ 62%] Building CXX object CMakeFiles/test_seed_client.dir/tests/test_seed_client.cpp.o
[ 62%] Building CXX object CMakeFiles/test_perms_seed.dir/tests/test_perms_seed.cpp.o
[ 75%] Linking CXX executable test_perms_seed
[ 75%] Built target test_perms_seed
[ 87%] Linking CXX executable test_seed_client_traversal
[100%] Linking CXX executable test_seed_client
[100%] Built target test_seed_client_traversal
[100%] Built target test_seed_client
[ 25%] Built target seed_client
[ 50%] Built target test_seed_client
[ 75%] Built target test_perms_seed
[100%] Built target test_seed_client_traversal
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libseed_client.so.1.0.0
-- Up-to-date: /usr/local/lib/libseed_client.so.1
-- Up-to-date: /usr/local/lib/libseed_client.so
-- Up-to-date: /usr/local/include/seed_client
-- Up-to-date: /usr/local/include/seed_client/seed_client.hpp
✅ seed-client instalado

╔════════════════════════════════════════════════════════════╗
║  🔨 Building crypto-transport Library                     ║
╚════════════════════════════════════════════════════════════╝

-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags (from Makefile):
-- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
-- libsodium lib:     /usr/local/lib/libsodium.so
-- libsodium include: /usr/local/include
-- Checking for module 'liblz4'
--   Found liblz4, version 1.9.4
-- libseed_client: /usr/local/lib/libseed_client.so
-- ========================================
-- crypto-transport Tests Configuration
-- ========================================
-- Test framework: Google Test
-- Tests: test_crypto, test_compression, test_integration, test_crypto_transport
-- ========================================
-- ========================================
-- crypto-transport Tests Configuration
-- ========================================
-- Test framework: Google Test
-- Tests: test_crypto, test_compression, test_integration
-- ========================================
-- ========================================
-- crypto-transport Library Configuration
-- ========================================
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags:
-- libsodium:
-- LZ4: 1.9.4
-- ========================================
-- Public Headers:
--   - include/crypto_transport/crypto.hpp
--   - include/crypto_transport/compression.hpp
--   - include/crypto_transport/utils.hpp
--   - include/crypto_transport/crypto_manager.hpp
--   - include/crypto_transport/transport.hpp
--   - include/crypto_transport/contexts.hpp
-- ========================================
-- Install destinations:
--   Library: /usr/local/lib
--   Headers: /usr/local/include/crypto_transport
--
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/crypto-transport/build
[ 13%] Building CXX object CMakeFiles/crypto_transport.dir/src/crypto.cpp.o
[ 13%] Building CXX object CMakeFiles/crypto_transport.dir/src/transport.cpp.o
[ 26%] Building CXX object CMakeFiles/crypto_transport.dir/src/compression.cpp.o
[ 26%] Building CXX object CMakeFiles/crypto_transport.dir/src/utils.cpp.o
[ 33%] Linking CXX shared library libcrypto_transport.so
[ 33%] Built target crypto_transport
[ 40%] Building CXX object tests/CMakeFiles/test_crypto.dir/test_crypto.cpp.o
[ 46%] Building CXX object tests/CMakeFiles/test_crypto_transport.dir/test_crypto_transport.cpp.o
[ 53%] Building CXX object tests/CMakeFiles/test_compression.dir/test_compression.cpp.o
[ 60%] Building CXX object tests/CMakeFiles/test_integration.dir/test_integration.cpp.o
[ 66%] Linking CXX executable test_crypto
[ 73%] Linking CXX executable test_compression
[ 73%] Built target test_crypto
[ 73%] Built target test_compression
[ 80%] Linking CXX executable test_integration
[ 86%] Building CXX object tests/CMakeFiles/test_integ_contexts.dir/test_integ_contexts.cpp.o
[ 86%] Built target test_integration
[ 93%] Linking CXX executable test_crypto_transport
/usr/bin/ld: aviso: libsodium.so.26, necesario para ../libcrypto_transport.so.1.0.0, podría entrar en conflicto con libsodium.so.23
[ 93%] Built target test_crypto_transport
[100%] Linking CXX executable test_integ_contexts
/usr/bin/ld: aviso: libsodium.so.26, necesario para ../libcrypto_transport.so.1.0.0, podría entrar en conflicto con libsodium.so.23
[100%] Built target test_integ_contexts
Installing system-wide...
[ 33%] Built target crypto_transport
[ 46%] Built target test_crypto
[ 60%] Built target test_compression
[ 73%] Built target test_integration
[ 86%] Built target test_crypto_transport
[100%] Built target test_integ_contexts
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libcrypto_transport.so.1.0.0
-- Up-to-date: /usr/local/lib/libcrypto_transport.so.1
-- Set runtime path of "/usr/local/lib/libcrypto_transport.so.1.0.0" to ""
-- Up-to-date: /usr/local/lib/libcrypto_transport.so
-- Up-to-date: /usr/local/include/crypto_transport/crypto.hpp
-- Up-to-date: /usr/local/include/crypto_transport/compression.hpp
-- Up-to-date: /usr/local/include/crypto_transport/utils.hpp
-- Up-to-date: /usr/local/include/crypto_transport/crypto_manager.hpp
-- Up-to-date: /usr/local/include/crypto_transport/transport.hpp
-- Up-to-date: /usr/local/include/crypto_transport/contexts.hpp

✅ crypto-transport installed to /usr/local/lib
lrwxrwxrwx 1 root root  24 may  6 04:47 /usr/local/lib/libcrypto_transport.so -> libcrypto_transport.so.1
lrwxrwxrwx 1 root root  28 may  6 04:47 /usr/local/lib/libcrypto_transport.so.1 -> libcrypto_transport.so.1.0.0
-rw-r--r-- 1 root root 51K may  6 05:11 /usr/local/lib/libcrypto_transport.so.1.0.0
🔨 Protobuf Unified System...
╔════════════════════════════════════════════════════════════╗
║  Protobuf Schema Generator                                 ║
╚════════════════════════════════════════════════════════════╝

📋 Schema: network_security.proto
📂 Output: /vagrant/protobuf

✅ libprotoc 3.21.12

🔨 Generating C++ protobuf files...
✅ Generated successfully:
-rwxrwxr-x 1 vagrant vagrant 916K may  6 05:11 /vagrant/protobuf/network_security.pb.cc
-rwxrwxr-x 1 vagrant vagrant 997K may  6 05:11 /vagrant/protobuf/network_security.pb.h

📊 Statistics:
network_security.pb.cc: 20782 lines
network_security.pb.h:  24569 lines

🐍 Generating Python protobuf files...
✅ network_security_pb2.py: 141 lines

📦 Distribuyendo protobuf unificado a componentes...
✅ Copiado a sniffer
✅ Copiado a ml-detector
✅ Copiado a firewall
🎯 Protobuf unificado distribuido a 3 componentes

╔════════════════════════════════════════════════════════════╗
║  ✅ Protobuf generation complete                           ║
╚════════════════════════════════════════════════════════════╝

🎯 Next steps:
1. Rebuild sniffer: cd /vagrant/sniffer && make
2. Rebuild ml-detector: cd /vagrant/ml-detector/build && cmake .. && make
3. Rebuild firewall: cd /vagrant/firewall-acl-agent/build && cmake .. && make


╔════════════════════════════════════════════════════════════╗
║  🔨 Building etcd-client Library                          ║
╚════════════════════════════════════════════════════════════╝

Dependencies:
✅ proto-unified
✅ crypto-transport-build

-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags (from Makefile):
-- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
-- ✅ Found seed-client: /usr/local/lib/libseed_client.so
-- Checking for module 'liblz4'
--   Found liblz4, version 1.9.4
-- ✅ LZ4 found
-- Found OpenSSL: /usr/lib/x86_64-linux-gnu/libcrypto.so (found version "3.0.19")  
-- ========================================
-- etcd-client Tests Configuration
-- ========================================
-- Tests configured:
--   - test_compression (crypto-transport)
--   - test_encryption (crypto-transport)
--   - test_pipeline (crypto-transport)
--   - test_put_config_integration (etcd_client)
--   - test_hmac_client (Day 53 - HMAC unit tests)
--   - test_hmac_integration_client (Day 53 - requires etcd-server)
--   - test_service_discovery (Day 59 - requires etcd-server)
--   ⚠️  test_etcd_client_hmac_grace_period (DISABLED - requires GTest)
-- ========================================
-- OpenSSL: 3.0.19
-- ========================================
-- ========================================
-- etcd-client Library Configuration
-- ========================================
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags:
-- crypto-transport: Found
--   Encryption: ChaCha20-Poly1305
--   Compression: LZ4
--
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/etcd-client/build
[  5%] Building CXX object tests/CMakeFiles/test_pipeline.dir/test_pipeline.cpp.o
[ 10%] Building CXX object CMakeFiles/etcd_client.dir/src/etcd_client.cpp.o
[ 15%] Building CXX object tests/CMakeFiles/test_compression.dir/test_compression.cpp.o
[ 21%] Building CXX object tests/CMakeFiles/test_encryption.dir/test_encryption.cpp.o
[ 26%] Linking CXX executable test_compression
[ 31%] Linking CXX executable test_encryption
[ 31%] Built target test_compression
[ 36%] Building CXX object CMakeFiles/etcd_client.dir/src/config_loader.cpp.o
[ 36%] Built target test_encryption
[ 42%] Building CXX object CMakeFiles/etcd_client.dir/src/http_client.cpp.o
[ 47%] Linking CXX executable test_pipeline
[ 47%] Built target test_pipeline
[ 52%] Building CXX object CMakeFiles/etcd_client.dir/src/component_registration.cpp.o
[ 57%] Linking CXX shared library libetcd_client.so
[ 57%] Built target etcd_client
[ 63%] Building CXX object tests/CMakeFiles/test_hmac_client.dir/test_hmac_client.cpp.o
[ 68%] Building CXX object tests/CMakeFiles/test_service_discovery.dir/test_service_discovery.cpp.o
[ 73%] Building CXX object tests/CMakeFiles/test_put_config_integration.dir/test_put_config_integration.cpp.o
[ 78%] Building CXX object tests/CMakeFiles/test_hmac_integration_client.dir/test_hmac_integration_client.cpp.o
[ 84%] Linking CXX executable test_service_discovery
[ 84%] Built target test_service_discovery
[ 89%] Linking CXX executable test_hmac_client
[ 89%] Built target test_hmac_client
[ 94%] Linking CXX executable test_hmac_integration_client
[ 94%] Built target test_hmac_integration_client
[100%] Linking CXX executable test_put_config_integration
[100%] Built target test_put_config_integration
Installing system-wide...
[ 26%] Built target etcd_client
[ 36%] Built target test_compression
[ 47%] Built target test_encryption
[ 57%] Built target test_pipeline
[ 68%] Built target test_put_config_integration
[ 78%] Built target test_hmac_client
[ 89%] Built target test_hmac_integration_client
[100%] Built target test_service_discovery
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libetcd_client.so.1.0.0
-- Up-to-date: /usr/local/lib/libetcd_client.so.1
-- Set runtime path of "/usr/local/lib/libetcd_client.so.1.0.0" to ""
-- Up-to-date: /usr/local/lib/libetcd_client.so
-- Up-to-date: /usr/local/include/etcd_client/etcd_client.hpp
-- Up-to-date: /usr/local/include/etcd_client
-- Up-to-date: /usr/local/include/etcd_client/etcd_client.hpp

✅ etcd-client installed to /usr/local/lib

Verifying library size and methods...
lrwxrwxr-x 1 vagrant vagrant 19 may  6 05:12 /vagrant/etcd-client/build/libetcd_client.so -> libetcd_client.so.1
lrwxrwxrwx 1 root root   19 may  6 04:48 /usr/local/lib/libetcd_client.so -> libetcd_client.so.1
lrwxrwxrwx 1 root root   23 may  6 04:48 /usr/local/lib/libetcd_client.so.1 -> libetcd_client.so.1.0.0
-rw-r--r-- 1 root root 1,1M may  6 05:12 /usr/local/lib/libetcd_client.so.1.0.0
Public methods: 49

╔════════════════════════════════════════════════════════════╗
║  🔌 Building plugin-loader Library (PHASE 1)              ║
╚════════════════════════════════════════════════════════════╝

Phase: 1 — no crypto, no seed-client (ADR-012)
Auth:  PHASE 2 (ADR-013, seed-client DAY 95-96)

-- The CXX compiler identification is GNU 12.2.0
-- The C compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/bin/cc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Build type: Release
-- C++ Standard: 20
-- CXX Flags (from Makefile):
-- libsodium: /usr/local/lib/libsodium.so
-- MLD_PLUGIN_PUBKEY_HEX: read from runtime file (DEBT-PUBKEY-RUNTIME-001)
-- ========================================
-- plugin-loader Library Configuration
-- ========================================
-- Build type: Release
-- C++ Standard: 20
-- Phase: 2 — Ed25519 plugin verification (ADR-025)
--   Auth: PHASE 2 (ADR-013, seed-client DAY 95-96)
-- Public Headers:
--   - include/plugin_loader/plugin_api.h
--   - include/plugin_loader/plugin_loader.hpp
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/plugin-loader/build
[ 50%] Building CXX object CMakeFiles/plugin_loader.dir/src/plugin_loader.cpp.o
[100%] Linking CXX shared library libplugin_loader.so
[100%] Built target plugin_loader
Installing system-wide...
[100%] Built target plugin_loader
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/lib/libplugin_loader.so.1.0.0
-- Up-to-date: /usr/local/lib/libplugin_loader.so.1
-- Set runtime path of "/usr/local/lib/libplugin_loader.so.1.0.0" to ""
-- Up-to-date: /usr/local/lib/libplugin_loader.so
-- Up-to-date: /usr/local/include/plugin_loader/plugin_api.h
-- Up-to-date: /usr/local/include/plugin_loader/plugin_loader.hpp

✅ plugin-loader installed to /usr/local/lib
lrwxrwxrwx 1 root root  21 may  6 04:47 /usr/local/lib/libplugin_loader.so -> libplugin_loader.so.1
lrwxrwxrwx 1 root root  25 may  6 04:47 /usr/local/lib/libplugin_loader.so.1 -> libplugin_loader.so.1.0.0
-rw-r--r-- 1 root root 71K may  6 05:13 /usr/local/lib/libplugin_loader.so.1.0.0

╔════════════════════════════════════════════════════════════╗
║  🔌 Building Test Message Plugin (ADR-025 integration)    ║
╚════════════════════════════════════════════════════════════╝
-- The CXX compiler identification is GNU 12.2.0
-- The C compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/bin/cc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/plugins/test-message/build
[ 50%] Building CXX object CMakeFiles/plugin_test_message.dir/plugin_test_message.cpp.o
[100%] Linking CXX shared library libplugin_test_message.so
[100%] Built target plugin_test_message
✅ libplugin_test_message.so deployed to /usr/lib/ml-defender/plugins/

╔════════════════════════════════════════════════════════════╗
║  🔨 Building etcd-server [debug]                     ║
╚════════════════════════════════════════════════════════════╝

Build dir: /vagrant/etcd-server/build-debug
Flags: -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG -DCMAKE_C_FLAGS=-std=c11 -g -O0 -fno-omit-frame-pointer -DDEBUG

-- ========================================
-- etcd-server Configuration
-- ========================================
-- Build type: Debug
-- C++ Standard: 20
-- CXX Flags (from Makefile): -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- ✅ OpenSSL found - HMAC support enabled
--    Version: 3.0.19
--    Include: /usr/include
--    Libraries: /usr/lib/x86_64-linux-gnu/libssl.so;/usr/lib/x86_64-linux-gnu/libcrypto.so
-- ✅ libsodium found - Using ChaCha20-Poly1305 + randombytes
-- ✅ LZ4 found - Compression enabled
-- ✅ Found crypto-transport library: /usr/local/lib/libcrypto_transport.so
-- ✅ Found crypto-transport headers: /usr/local/include
-- ✅ Found seed-client library: /usr/local/lib/libseed_client.so
-- ✅ Found seed-client headers: /usr/local/include
-- ========================================
-- Building Tests
-- ========================================
-- ✅ Test executables configured:
--    - test_secrets_manager
--    - test_hmac_integration
-- ========================================
-- ========================================
-- Build Configuration:
--   C++ Standard: 20
--   Build Type: Debug
--   CXX Flags: -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- ========================================
-- Dependencies:
--   crypto-transport: /usr/local/lib/libcrypto_transport.so
--   libsodium: sodium
--   LZ4: lz4
--   OpenSSL: /usr/lib/x86_64-linux-gnu/libssl.so;/usr/lib/x86_64-linux-gnu/libcrypto.so
-- ========================================
-- Sources:
--   - src/main.cpp
--   - src/etcd_server.cpp
--   - src/component_registry.cpp
--   - src/crypto_manager.cpp
--   - src/compression_lz4.cpp
--   - src/secrets_manager.cpp
-- ========================================
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/etcd-server/build-debug
[ 23%] Built target test_hmac_integration
[ 46%] Built target test_secrets_manager_simple
[100%] Built target etcd-server

✅ etcd-server built (debug)
🔨 Building RAG Security System [debug]...
-- Build type: Debug
-- Found llama.cpp: /vagrant/rag/../third_party/llama.cpp
-- ✅ Found llama shared library: /vagrant/rag/../third_party/llama.cpp/build/bin/libllama.so
-- 🔍 Buscando dependencias del sistema...
-- 🔍 Buscando FAISS library...
-- ✅ Found FAISS library: /usr/local/lib/libfaiss.so
-- ✅ Found FAISS headers: /usr/local/include
-- ✅ Found BLAS: /usr/lib/x86_64-linux-gnu/libblas.so
-- 🔍 Buscando ONNX Runtime...
-- ✅ Found ONNX Runtime: /usr/local/lib/libonnxruntime.so
-- ✅ Found ONNX headers: /usr/local/include
-- 🔍 Buscando etcd-client library...
-- ✅ Found etcd-client library: /usr/local/lib/libetcd_client.so
-- ✅ llama.cpp integration enabled
-- ✅ FAISS linked to rag-security
-- plugin-loader: /usr/local/lib/libplugin_loader.so
-- 🧪 Configurando tests FAISS...
-- ✅ test_faiss_basic configured
-- ✅ test_embedder configured
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- ✅ test_onnx_basic configured
--    ONNX include: /usr/local/include
--    ONNX library: /usr/local/lib/libonnxruntime.so
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--
-- ╔════════════════════════════════════════════════════════════╗
-- ║  RAG Security System - Build Configuration                ║
-- ╚════════════════════════════════════════════════════════════╝
--
-- 📦 Core Dependencies:
--    - httplib: /usr/local/include
--    - nlohmann/json: /usr/include
--    - llama.cpp: TRUE
--    - etcd-client: /usr/local/lib/libetcd_client.so
--    - threads: OK
--
-- 🔬 Phase 2A Dependencies:
--    - FAISS: TRUE
--      • Library: /usr/local/lib/libfaiss.so
--      • Include: /usr/local/include
--      • BLAS: /usr/lib/x86_64-linux-gnu/libblas.so
--    - ONNX Runtime: TRUE
--      • Library: /usr/local/lib/libonnxruntime.so
--      • Include: /usr/local/include
--
-- 🎯 Targets:
--    - rag-security (main executable)
--    - test_faiss_basic (FAISS integration test)
--    - test_onnx_basic (planned)
--
-- ═══════════════════════════════════════════════════════════
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/rag/build
[ 10%] Built target test_faiss_basic
[ 20%] Built target test_onnx_basic
[ 40%] Built target test_embedder
[ 45%] Linking CXX executable rag-security
[100%] Built target rag-security
✅ rag-security built (debug)
✅ Protobuf unificado generado y distribuido

╔════════════════════════════════════════════════════════════╗
║  🔨 Building RAG Ingester [debug]                    ║
╚════════════════════════════════════════════════════════════╝

Build dir: /vagrant/rag-ingester/build-debug
Flags: -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG -DCMAKE_C_FLAGS=-std=c11 -g -O0 -fno-omit-frame-pointer -DDEBUG

Copying protobuf files...
Running CMake and build...
-- Build type: Debug
-- C++ Standard: 20
-- CXX Flags (from Makefile): -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- ✅ Found etcd_client: /usr/local/lib/libetcd_client.so
-- ✅ Found crypto_transport: /usr/local/lib/libcrypto_transport.so
-- ✅ Found seed-client: /usr/local/lib/libseed_client.so
-- ✅ LZ4 found: 1.9.4
-- ✅ Found common-rag-ingester: /vagrant/common-rag-ingester/build/libcommon-rag-ingester.so
-- ✅ Found FAISS
-- ✅ Found ONNX Runtime: /usr/local/lib/libonnxruntime.so
-- ✅ protobuf headers: /vagrant/rag-ingester/build-debug/proto
-- ✅ crypto-transport headers: /vagrant/crypto-transport/include
-- ✅ reason_codes.hpp headers: /vagrant/common/include
-- ✅ OpenSSL headers: /usr/include
-- plugin-loader: /usr/local/lib/libplugin_loader.so
-- ✅ test_config_parser_traversal registered (DEBT-SAFE-PATH-TEST-PRODUCTION-001)
--
-- === RAG Ingester Build Configuration ===
-- Build type: Debug
-- C++ standard: 20
-- CXX Flags: -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
--
-- Required libraries:
--   etcd-client:      /usr/local/lib/libetcd_client.so
--   crypto-transport: /usr/local/lib/libcrypto_transport.so
--   protobuf:         /usr/lib/x86_64-linux-gnu/libprotobuf.so
--   OpenSSL:          3.0.19
--
-- Optional libraries:
--   common-rag-ingester: ENABLED
--   FAISS: ENABLED
--   ONNX Runtime: ENABLED
--
-- Day 40 Components:
--   EventLoader:   crypto-transport (.pb protobuf)
--   FileWatcher:   inotify IN_CLOSE_WRITE (*.pb)
--   MetadataDB:    Producer (write)
--   FAISS:         Persistence enabled
--   Features:      101 (61 base + 40 embedded)
--
-- Day 67 Components:
--   CsvFileWatcher:  inotify IN_MODIFY + offset (append-only CSV)
--   CsvEventLoader:  127-col CSV parser + HMAC-SHA256 verification
--   Feature vector:  62 raw NetworkFeatures (Section 2)
--   WAL mode:        SQLite WAL required for streaming inserts
--
-- Day 69 Components:
--   CsvDirWatcher:          inotify on directory, daily rotation
--   FirewallCsvEventLoader: 7-col CSV parser + HMAC-SHA256
--   Source A (ml-detector): CsvDirWatcher → FAISS + MetadataDB INSERT
--   Source B (firewall):    CsvFileWatcher → MetadataDB UPDATE
--   Correlation:            provisional by src_ip+ts_window (±5s)
--                           clean path via trace_id (Day 72)
--
-- Day 72 Components:
--   Idempotency guard:      exists() before embed+index (FAISS/DB sync)
--   trace_id_generator:     header-only, include/utils/
--                           SHA256(src|dst|attack|bucket) prefix 16B
--                           O(1), zero-coordination, deterministic
--                           Sentinel: empty IP → 0.0.0.0 (warn logged)
--                           Sentinel: empty attack → unknown (warn logged)
--   MetadataDB schema:      complete from birth (no ALTER TABLE needed)
--   test_trace_id:          6 test groups incl. edge cases
--
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
--
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/rag-ingester/build-debug
[  4%] Built target csv_file_watcher
[ 13%] Built target file_watcher
[ 13%] Built target csv_event_loader
[ 15%] Building CXX object CMakeFiles/event_loader.dir/src/event_loader.cpp.o
[ 20%] Built target firewall_csv_event_loader
[ 24%] Built target csv_dir_watcher
[ 31%] Built target test_config_parser
[ 35%] Built target test_file_watcher
[ 42%] Built target test_config_parser_traversal
[ 46%] Built target test_csv_file_watcher
[ 51%] Built target test_csv_event_loader
[ 55%] Built target test_firewall_csv_event_loader
[ 60%] Built target test_csv_dir_watcher
[ 62%] Building CXX object CMakeFiles/event_loader.dir/proto/network_security.pb.cc.o
[ 66%] Built target test_trace_id
[ 68%] Linking CXX static library libevent_loader.a
[ 68%] Built target event_loader
[ 71%] Building CXX object CMakeFiles/rag-ingester.dir/proto/network_security.pb.cc.o
[ 73%] Linking CXX executable rag-ingester
[100%] Built target rag-ingester

✅ RAG Ingester built (debug)

╔════════════════════════════════════════════════════════════╗
║  🔨 Building ML Detector [debug]                     ║
╚════════════════════════════════════════════════════════════╝

Build dir: /vagrant/ml-detector/build-debug
Flags: -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG -DCMAKE_C_FLAGS=-std=c11 -g -O0 -fno-omit-frame-pointer -DDEBUG

Copying protobuf files...
Running CMake and build...
-- Build type: Debug
-- C++ Standard: 20
-- CXX Flags (from Makefile): -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- Found nlohmann_json
-- Found ZeroMQ: 4.3.4
-- Found Protobuf: 3.21.12
-- Found ONNX Runtime (manual): /usr/local/lib/libonnxruntime.so
-- Found nlohmann/json: 3.11.2
-- Found spdlog: 1.10.0
-- Could NOT find c-ares (missing: c-ares_DIR)
-- Found RE2 via pkg-config.
-- Found etcd-cpp-api: 0.15.3
-- ✅ Found etcd-client library: /vagrant/etcd-client/build/libetcd_client.so
-- ✅ Found crypto-transport library: /usr/local/lib/libcrypto_transport.so
-- ✅ Found crypto-transport headers: /usr/local/include
-- ✅ Found seed-client: /usr/local/lib/libseed_client.so
-- ✅ LZ4 found: 1.9.4
-- ✅ Protobuf unificado encontrado: /vagrant/ml-detector/build-debug/proto/network_security.pb.cc
--
-- 🔗 Setting up models symlink...
--    Source: /vagrant/ml-detector/models
--    Target: /vagrant/ml-detector/build-debug/models
-- ✅ Models symlink created successfully
--    Config will use: models/production/
--    Points to:       ../models/production/
--
-- 🔗 Setting up config symlink...
--    Source: /vagrant/ml-detector/config
--    Target: /vagrant/ml-detector/build-debug/config
-- ✅ Config symlink created successfully
--
-- Found OpenSSL: 3.0.19
-- ✅ test_rag_logger_artifact_save registered (DAY 75)
-- ✅ test_zmq_memory_overflow registered (DEBT-INTEGER-OVERFLOW-TEST-001)
-- ✅ test_csv_event_writer registered
-- ✅ test_csv_feature_extraction registered
--
-- ─── Test suite ──────────────────────────────
--   Unit:
--     test_classifier             (stub)
--     test_feature_extractor       (stub)
--     test_model_loader            (stub)
--     test_ransomware_detector_unit
--     test_detectors               (standalone, no ctest)
--   Integration:
--     test_ransomware_detector_integration
--     test_pipeline                (stub)
--   Day 64 — CSV pipeline:
--     test_csv_event_writer
--     test_csv_feature_extraction
--     test_etcd_client_hmac
-- ─────────────────────────────────────────────
--
-- ✅ Found plugin-loader: /usr/local/lib/libplugin_loader.so
--
-- ======================================
-- ML Detector Tricapa - Configuration
-- ======================================
-- Build type:        Debug
-- C++ compiler:      GNU 12.2.0
-- C++ standard:      20
-- Install prefix:    /usr/local
-- CXX Flags:         -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
--
-- Dependencies:
--   ZeroMQ:          4.3.4
--   Protobuf:        3.21.12
--   ONNX Runtime:    Found
--   nlohmann/json:   Found
--   spdlog:          Found
--   etcd-client:     TRUE
--   crypto-transport: TRUE
--   etcd-cpp-api:    TRUE
--
-- Options:
--   Build tests:     ON
--
-- 🎯 Single Source of Truth:
--   Models:          /vagrant/ml-detector/models → build/models (symlink)
--   Config:          /vagrant/ml-detector/config → build/config (symlink)
--   Protobuf:        /vagrant/ml-detector/build-debug/proto/network_security.pb.cc (unificado)
--   Compiler Flags:  Controlled by root Makefile via PROFILE
-- ======================================
--
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/ml-detector/build-debug
[  3%] Built target test_classifier
[  7%] Built target test_feature_extractor
[ 11%] Built target ransomware_detector
[ 15%] Built target test_model_loader
[ 17%] Building CXX object tests/CMakeFiles/test_rag_logger_artifact_save.dir/unit/test_rag_logger_artifact_save.cpp.o
[ 19%] Linking CXX executable test_pipeline
[ 28%] Built target test_detectors
[ 32%] Built target test_zmq_memory_overflow
[ 34%] Built target test_pipeline
[ 36%] Building CXX object tests/CMakeFiles/test_csv_event_writer.dir/integration/test_csv_event_writer.cpp.o
[ 38%] Building CXX object tests/CMakeFiles/test_csv_feature_extraction.dir/integration/test_csv_feature_extraction.cpp.o
[ 40%] Linking CXX executable test_etcd_client_hmac
[ 44%] Built target test_etcd_client_hmac
[ 46%] Building CXX object tests/CMakeFiles/test_csv_event_writer.dir/__/src/csv_event_writer.cpp.o
[ 48%] Building CXX object tests/CMakeFiles/test_rag_logger_artifact_save.dir/__/proto/network_security.pb.cc.o
[ 50%] Building CXX object tests/CMakeFiles/test_csv_feature_extraction.dir/__/src/csv_event_writer.cpp.o
[ 51%] Building CXX object tests/CMakeFiles/test_csv_feature_extraction.dir/__/proto/network_security.pb.cc.o
[ 53%] Building CXX object tests/CMakeFiles/test_csv_event_writer.dir/__/proto/network_security.pb.cc.o
[ 55%] Linking CXX executable test_rag_logger_artifact_save
[ 57%] Building CXX object CMakeFiles/ml-detector.dir/src/main.cpp.o
[ 57%] Built target test_rag_logger_artifact_save
[ 61%] Built target test_ransomware_detector_unit
[ 63%] Building CXX object CMakeFiles/ml-detector.dir/src/feature_extractor.cpp.o
[ 65%] Linking CXX executable test_csv_feature_extraction
[ 65%] Built target test_csv_feature_extraction
[ 67%] Building CXX object CMakeFiles/ml-detector.dir/src/rag_logger.cpp.o
[ 69%] Linking CXX executable test_csv_event_writer
[ 69%] Built target test_csv_event_writer
[ 71%] Building CXX object CMakeFiles/ml-detector.dir/src/zmq_handler.cpp.o
[ 73%] Building CXX object CMakeFiles/ml-detector.dir/src/csv_event_writer.cpp.o
[ 75%] Building CXX object CMakeFiles/ml-detector.dir/proto/network_security.pb.cc.o
[ 76%] Linking CXX executable ml-detector
[100%] Built target ml-detector

✅ ML Detector built (debug)

╔════════════════════════════════════════════════════════════╗
║  🔨 Building Sniffer [debug]                         ║
╚════════════════════════════════════════════════════════════╝

Build dir: /vagrant/sniffer/build-debug
Flags: -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG -DCMAKE_C_FLAGS=-std=c11 -g -O0 -fno-omit-frame-pointer -DDEBUG

Copying protobuf files...
Running CMake and build...
-- Build type: Debug
-- C++ Standard: 20
-- CXX Flags (from Makefile): -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- Checking for module 'libsnappy'
--   Package 'libsnappy', required by 'virtual:world', not found
-- 🔍 Buscando etcd-client library...
-- ✅ Found etcd-client library: /vagrant/etcd-client/build/libetcd_client.so
-- 🔍 Buscando crypto-transport library...
-- ✅ Found crypto-transport library: /usr/local/lib/libcrypto_transport.so
-- ✅ Found crypto-transport includes: /usr/local/include
-- ✅ Found libsodium: /usr/local/lib/libsodium.so
-- ✅ Found seed-client: /usr/local/lib/libseed_client.so
-- ✅ Found plugin-loader: /usr/local/lib/libplugin_loader.so
-- ✅ Protobuf unificado encontrado: /vagrant/sniffer/build-debug/proto/network_security.pb.cc
--
-- === ⚡ Enhanced Sniffer Configuration ===
-- 📋 Build Info:
--    Type: Debug
--    C++ standard: 20
--    Compiler: GNU 12.2.0
--    CXX Flags: -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
--
-- 🔧 Core Dependencies:
--    libbpf: 1.4.6 (Variant A)
--    ZeroMQ: 4.3.4
--    jsoncpp: 1.9.5
--    Protobuf: 3.21.12
--
-- 🗜️ Compression Support (MANDATORY):
--    ✅ LZ4: 1.9.4 (required)
--    ✅ Zstandard: 1.5.4 (required)
--    ⚪ Snappy: not available (optional)
--
-- 🚀 Optional Features:
--    ✅ etcd client: enabled
--    ✅ NUMA optimization: enabled
--
-- 📦 Build Artifacts:
--    Binary: /vagrant/sniffer/build-debug/sniffer
--    eBPF program: /vagrant/sniffer/build-debug/sniffer.bpf.o
--    Configuration: /vagrant/sniffer/build-debug/config/sniffer.json
--
-- 🎯 Sniffer Capabilities:
--    ✅ Multi-threading support
--    ✅ eBPF/XDP high-performance packet capture
--    ✅ Mandatory LZ4/Zstd compression
--    ✅ Protobuf serialization
--    ✅ ZeroMQ communication
--    ✅ etcd-client library: enabled
--    ✅ crypto-transport library: enabled
--    ✅ libsodium: enabled
--    ✅ plugin-loader: enabled (ADR-012 PHASE 1b)
--    🔐 Encryption ready (via etcd tokens)
--
-- 🎯 Single Source of Truth:
--    Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
--
-- 🧪 Unit Test: test_payload_analyzer configured
-- 🧪 Unit Test: test_sharded_flow_full_contract configured (Day 46 - ISSUE-003)
-- 🧪 Unit Test: test_ring_consumer_protobuf configured (Day 46 - 40 features)
-- 🧪 Unit Test: test_proto3_embedded_serialization configured (DAY 75 regression)
-- 🧪 Unit Test: test_smb_scan_features configured (DAY 92 - SYN-1, SYN-2)
-- 🧪 Unit Test: test_sharded_flow_multithread configured (Day 46 - Concurrency)
-- 🧪 Variant B Test: test_pcap_backend_lifecycle configured
-- 🧪 Variant B Test: test_pcap_backend_poll_null configured
-- 🧪 Variant B Test: test_pcap_backend_callback configured
-- 🧪 Variant B Test: test_pcap_backend_error configured
-- 🧪 Variant B Test: test_pcap_proto_parse_tcp configured
-- 🧪 Variant B Test: test_pcap_proto_parse_udp configured
-- 🧪 Variant B Test: test_pcap_backend_stress configured
-- 🧪 Variant B Test: test_pcap_backend_regression configured
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/sniffer/build-debug
[  1%] Built target bpf_program
[  4%] Built target test_payload_analyzer
[  5%] Building CXX object CMakeFiles/test_proto3_embedded_serialization.dir/tests/test_proto3_embedded_serialization.cpp.o
[ 14%] Built target test_sharded_flow_full_contract
[ 15%] Building CXX object CMakeFiles/test_smb_scan_features.dir/tests/test_smb_scan_features.cpp.o
[ 16%] Building CXX object CMakeFiles/test_ring_consumer_protobuf.dir/tests/test_ring_consumer_protobuf.cpp.o
[ 17%] Building CXX object CMakeFiles/test_sharded_flow_multithread.dir/tests/test_sharded_flow_multithread.cpp.o
[ 18%] Building CXX object CMakeFiles/test_proto3_embedded_serialization.dir/proto/network_security.pb.cc.o
[ 19%] Building CXX object CMakeFiles/test_smb_scan_features.dir/proto/network_security.pb.cc.o
[ 20%] Building CXX object CMakeFiles/test_ring_consumer_protobuf.dir/src/userspace/ml_defender_features.cpp.o
[ 21%] Building CXX object CMakeFiles/test_sharded_flow_multithread.dir/src/userspace/ml_defender_features.cpp.o
[ 22%] Building CXX object CMakeFiles/test_sharded_flow_multithread.dir/proto/network_security.pb.cc.o
[ 23%] Building CXX object CMakeFiles/test_ring_consumer_protobuf.dir/proto/network_security.pb.cc.o
[ 25%] Linking CXX executable test_smb_scan_features
[ 25%] Built target test_smb_scan_features
[ 26%] Linking CXX executable test_proto3_embedded_serialization
[ 29%] Built target test_pcap_backend_lifecycle
[ 32%] Built target test_pcap_backend_poll_null
[ 32%] Built target test_proto3_embedded_serialization
[ 35%] Built target test_pcap_backend_callback
[ 36%] Building CXX object CMakeFiles/test_pcap_proto_parse_tcp.dir/tests/test_pcap_proto_parse_tcp.cpp.o
[ 37%] Building CXX object CMakeFiles/test_pcap_backend_error.dir/tests/test_pcap_backend_error.cpp.o
[ 38%] Linking CXX executable test_sharded_flow_multithread
[ 45%] Built target test_sharded_flow_multithread
[ 46%] Building CXX object CMakeFiles/test_pcap_backend_error.dir/src/userspace/pcap_backend.cpp.o
[ 47%] Linking CXX executable test_ring_consumer_protobuf
[ 48%] Building CXX object CMakeFiles/test_pcap_proto_parse_tcp.dir/proto/network_security.pb.cc.o
[ 50%] Building CXX object CMakeFiles/test_pcap_proto_parse_udp.dir/tests/test_pcap_proto_parse_udp.cpp.o
[ 51%] Linking CXX executable test_pcap_backend_error
[ 51%] Built target test_pcap_backend_error
[ 52%] Building CXX object CMakeFiles/test_pcap_backend_stress.dir/tests/test_pcap_backend_stress.cpp.o
[ 59%] Built target test_ring_consumer_protobuf
[ 60%] Building CXX object CMakeFiles/test_pcap_backend_regression.dir/tests/test_pcap_backend_regression.cpp.o
[ 61%] Building CXX object CMakeFiles/test_pcap_backend_stress.dir/src/userspace/pcap_backend.cpp.o
[ 62%] Building CXX object CMakeFiles/test_pcap_proto_parse_udp.dir/proto/network_security.pb.cc.o
[ 63%] Linking CXX executable test_pcap_backend_stress
[ 64%] Building CXX object CMakeFiles/test_pcap_backend_regression.dir/src/userspace/pcap_backend.cpp.o
[ 64%] Built target test_pcap_backend_stress
[ 65%] Linking CXX executable test_pcap_backend_regression
[ 65%] Built target test_pcap_backend_regression
[ 66%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/main.cpp.o
[ 67%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/ebpf_loader.cpp.o
[ 68%] Linking CXX executable test_pcap_proto_parse_tcp
[ 68%] Built target test_pcap_proto_parse_tcp
[ 69%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/ring_consumer.cpp.o
[ 70%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/thread_manager.cpp.o
[ 72%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/feature_logger.cpp.o
[ 72%] Linking CXX executable test_pcap_proto_parse_udp
[ 72%] Built target test_pcap_proto_parse_udp
[ 73%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/dual_nic_manager.cpp.o
[ 75%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/ransomware_feature_processor.cpp.o
[ 76%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/bpf_map_manager.cpp.o
[ 77%] Building CXX object CMakeFiles/sniffer.dir/proto/network_security.pb.cc.o
[ 78%] Building CXX object CMakeFiles/sniffer.dir/src/userspace/ml_defender_features.cpp.o
[ 79%] Linking CXX executable sniffer
[100%] Built target sniffer

✅ Sniffer built (debug)

╔════════════════════════════════════════════════════════════╗
║  🔨 Building Firewall ACL Agent [debug]              ║
╚════════════════════════════════════════════════════════════╝

Build dir: /vagrant/firewall-acl-agent/build-debug
Flags: -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG -DCMAKE_C_FLAGS=-std=c11 -g -O0 -fno-omit-frame-pointer -DDEBUG

Copying protobuf files...
Running CMake and build...
-- Build type: Debug
-- C++ Standard: 20
-- CXX Flags (from Makefile): -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- ⚠️  backtrace library not found - using execinfo.h fallback
-- ✅ Found crypto-transport: /usr/local/lib/libcrypto_transport.so
-- ✅ Found seed-client: /usr/local/lib/libseed_client.so
-- ✅ LZ4 found: 1.9.4
-- ✅ Found etcd-client library: /vagrant/etcd-client/build/libetcd_client.so
-- ✅ Protobuf unificado encontrado: /vagrant/firewall-acl-agent/build-debug/proto/network_security.pb.cc
-- ✅ Linking etcd-client library to firewall_core
-- plugin-loader: /usr/local/lib/libplugin_loader.so
-- ✅ Unit tests enabled (including logger tests)
--
-- ╔════════════════════════════════════════════════════════╗
-- ║  ML Defender - Firewall ACL Agent Configuration       ║
-- ║  Day 50: Comprehensive Observability Integration      ║
-- ╚════════════════════════════════════════════════════════╝
--
-- Version:           1.0.0
-- C++ Standard:      C++20
-- Build Type:        Debug
-- CXX Flags:         -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
--
-- ✅ Components:
--   Logger:          IMPLEMENTED (async + payload storage)
--   Observability:   IMPLEMENTED (Day 50 - microsecond logging)
--   Crash Diag:      IMPLEMENTED (backtrace + state dumps)
--   Metrics:         TODO (unified system)
--   ACL Intelligence: TODO (Phase 2+)
--
-- 🔬 Day 50 Observability:
--   Headers:         firewall_observability_logger.hpp
--                    crash_diagnostics.hpp
--   Log Levels:      DEBUG, INFO, BATCH, IPSET, WARN, ERROR, CRASH
--   Precision:       Microsecond timestamps
--   Thread Safety:   Mutex-protected + atomic counters
--   Crash Handling:  Signal handlers with backtrace
--   Backtrace Lib:   FALSE
--
-- 📊 Logging Output:
--   Observability:   /vagrant/logs/firewall-acl-agent/firewall_detailed.log
--   JSON metadata:   /vagrant/logs/blocked/TIMESTAMP.json
--   Protobuf payload: /vagrant/logs/blocked/TIMESTAMP.proto
--   Format:          Timestamp-based (unique, sortable)
--
-- 🔗 RAG Integration Ready:
--   ✅ Structured JSON for vector DB
--   ✅ Full protobuf for forensic analysis
--   ✅ Async design (non-blocking)
--
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
--
-- ⚡ Performance Target: 1M+ packets/sec DROP rate
-- 🎯 Design Philosophy: Via Appia Quality
-- 🔬 Day 50 Motto: Fiat Lux - Let there be light
--
-- ╚════════════════════════════════════════════════════════╝
--
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/firewall-acl-agent/build-debug
[  6%] Building CXX object CMakeFiles/firewall_core.dir/src/core/logger.cpp.o
[ 25%] Building CXX object CMakeFiles/firewall_core.dir/src/api/zmq_subscriber.cpp.o
[ 25%] Building CXX object CMakeFiles/firewall_core.dir/src/core/batch_processor.cpp.o
[ 25%] Building CXX object CMakeFiles/firewall_core.dir/proto/network_security.pb.cc.o
[ 31%] Linking CXX static library libfirewall_core.a
[ 56%] Built target firewall_core
[ 62%] Building CXX object CMakeFiles/firewall-acl-agent.dir/src/main.cpp.o
[ 68%] Building CXX object CMakeFiles/firewall_tests.dir/tests/unit/test_logger.cpp.o
[ 75%] Linking CXX executable firewall_tests
[ 81%] Linking CXX executable firewall-acl-agent
[100%] Built target firewall_tests
[100%] Built target firewall-acl-agent

✅ Firewall built (debug)

╔════════════════════════════════════════════════════════════╗
║  🔨 Building argus-network-isolate [ADR-042 IRP]          ║
╚════════════════════════════════════════════════════════════╝
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Build type: Debug
-- CXX Flags: -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0
-- Performing Test CMAKE_HAVE_LIBC_PTHREAD
-- Performing Test CMAKE_HAVE_LIBC_PTHREAD - Success
-- Found Threads: TRUE  
-- Found nlohmann_json: /usr/share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake (found version "3.11.2")
-- ========================================
-- argus-network-isolate — ADR-042 IRP
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/tools/build-argus-network-isolate
[ 33%] Building CXX object CMakeFiles/argus-network-isolate.dir/isolate.cpp.o
[ 66%] Building CXX object CMakeFiles/argus-network-isolate.dir/main.cpp.o
[100%] Linking CXX executable argus-network-isolate
[100%] Built target argus-network-isolate
✅ argus-network-isolate built
── Instalando argus-network-isolate en /usr/local/bin/ ──
✅ argus-network-isolate instalado
🔍 Verificando artefactos de build...
✅ Artefactos de build presentes
[6/8] Desplegando modelos ML...
✅ Modelos ML desplegados en /etc/ml-defender/models/
[6b/8] Firmando plugins...
Firmando plugins (ADR-025 D1)...

══ Firma de plugins (ADR-025 D1) ══
→ Plugin firmado: libplugin_test_message.so → libplugin_test_message.so.sig (64 bytes)
→ Plugin firmado: libplugin_xgboost.so → libplugin_xgboost.so.sig (64 bytes)
✅ 2 plugin(s) firmados correctamente
[7/8] Verificando provisioning...

╔════════════════════════════════════════════════════════════╗
║  🔍 TEST-PROVISION-1 — CI Gate PHASE 3                   ║
╚════════════════════════════════════════════════════════════╝

── Check 1/8: Claves criptográficas ──

══ Verificación de integridad ══
✅ etcd-server: OK
✅ sniffer: OK
✅ ml-detector: OK
✅ firewall-acl-agent: OK
✅ rag-ingester: OK
✅ rag-security: OK

✅ Todas las claves verificadas correctamente
✅ Check 1/8 OK

── Check 2/8: Firmas de plugins (producción) ──

══ check-plugins (DEBT-SIGN-AUTO, ADR-025) ══
→ Modo: PRODUCCIÓN — solo verificar, nunca firmar
→ libplugin_test_message.so: .sig válido — skip
→ libplugin_xgboost.so: .sig válido — skip

✅ 2 plugin(s) ya firmados y válidos (skip)
✅ check-plugins completado — todos los plugins firmados y verificados
✅ Check 2/8 OK

── Check 3/8: Configs de producción (sin dev plugins) ──
🔍 Validando que libplugin_hello NO está en configs de producción...
✅ validate-prod-configs: libplugin_hello ausente en todos los configs
✅ Check 3/8 OK

── Check 4/8: build-active symlinks ──
✅ Check 4/8 OK

── Check 5/8: systemd units instalados ──
✅ Check 5/8 OK


── Check 6/8: Permisos ficheros sensibles ──
✅ Check 6/8 OK

── Check 7/8: Consistencia JSONs con plugins reales ──
✅ Sin plugins activos en configs de producción (correcto)
✅ Check 7/8 OK

── Check 8/8: apparmor-utils instalado ──
✅ Check 8/8 OK
╔════════════════════════════════════════════════════════════╗
║  ✅ TEST-PROVISION-1 PASSED — entorno listo               ║
╚════════════════════════════════════════════════════════════╝

[8/8] Arrancando pipeline...

╔════════════════════════════════════════════════════════════╗
║  🔍 TEST-PROVISION-1 — CI Gate PHASE 3                   ║
╚════════════════════════════════════════════════════════════╝

── Check 1/8: Claves criptográficas ──

══ Verificación de integridad ══
✅ etcd-server: OK
✅ sniffer: OK
✅ ml-detector: OK
✅ firewall-acl-agent: OK
✅ rag-ingester: OK
✅ rag-security: OK

✅ Todas las claves verificadas correctamente
✅ Check 1/8 OK

── Check 2/8: Firmas de plugins (producción) ──

══ check-plugins (DEBT-SIGN-AUTO, ADR-025) ══
→ Modo: PRODUCCIÓN — solo verificar, nunca firmar
→ libplugin_test_message.so: .sig válido — skip
→ libplugin_xgboost.so: .sig válido — skip

✅ 2 plugin(s) ya firmados y válidos (skip)
✅ check-plugins completado — todos los plugins firmados y verificados
✅ Check 2/8 OK

── Check 3/8: Configs de producción (sin dev plugins) ──
🔍 Validando que libplugin_hello NO está en configs de producción...
✅ validate-prod-configs: libplugin_hello ausente en todos los configs
✅ Check 3/8 OK

── Check 4/8: build-active symlinks ──
✅ Check 4/8 OK

── Check 5/8: systemd units instalados ──
✅ Check 5/8 OK


── Check 6/8: Permisos ficheros sensibles ──
✅ Check 6/8 OK

── Check 7/8: Consistencia JSONs con plugins reales ──
✅ Sin plugins activos en configs de producción (correcto)
✅ Check 7/8 OK

── Check 8/8: apparmor-utils instalado ──
✅ Check 8/8 OK
╔════════════════════════════════════════════════════════════╗
║  ✅ TEST-PROVISION-1 PASSED — entorno listo               ║
╚════════════════════════════════════════════════════════════╝


╔════════════════════════════════════════════════════════════╗
║  🔨 Building etcd-server [debug]                     ║
╚════════════════════════════════════════════════════════════╝

Build dir: /vagrant/etcd-server/build-debug
Flags: -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS=-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG -DCMAKE_C_FLAGS=-std=c11 -g -O0 -fno-omit-frame-pointer -DDEBUG

-- ========================================
-- etcd-server Configuration
-- ========================================
-- Build type: Debug
-- C++ Standard: 20
-- CXX Flags (from Makefile): -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- ✅ OpenSSL found - HMAC support enabled
--    Version: 3.0.19
--    Include: /usr/include
--    Libraries: /usr/lib/x86_64-linux-gnu/libssl.so;/usr/lib/x86_64-linux-gnu/libcrypto.so
-- ✅ libsodium found - Using ChaCha20-Poly1305 + randombytes
-- ✅ LZ4 found - Compression enabled
-- ✅ Found crypto-transport library: /usr/local/lib/libcrypto_transport.so
-- ✅ Found crypto-transport headers: /usr/local/include
-- ✅ Found seed-client library: /usr/local/lib/libseed_client.so
-- ✅ Found seed-client headers: /usr/local/include
-- ========================================
-- Building Tests
-- ========================================
-- ✅ Test executables configured:
--    - test_secrets_manager
--    - test_hmac_integration
-- ========================================
-- ========================================
-- Build Configuration:
--   C++ Standard: 20
--   Build Type: Debug
--   CXX Flags: -std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG
-- ========================================
-- Dependencies:
--   crypto-transport: /usr/local/lib/libcrypto_transport.so
--   libsodium: sodium
--   LZ4: lz4
--   OpenSSL: /usr/lib/x86_64-linux-gnu/libssl.so;/usr/lib/x86_64-linux-gnu/libcrypto.so
-- ========================================
-- Sources:
--   - src/main.cpp
--   - src/etcd_server.cpp
--   - src/component_registry.cpp
--   - src/crypto_manager.cpp
--   - src/compression_lz4.cpp
--   - src/secrets_manager.cpp
-- ========================================
-- 🎯 Single Source of Truth:
--   Compiler Flags: Controlled by root Makefile via PROFILE
-- ========================================
-- Configuring done
-- Generating done
-- Build files have been written to: /vagrant/etcd-server/build-debug
[ 23%] Built target test_hmac_integration
[ 46%] Built target test_secrets_manager_simple
[100%] Built target etcd-server

✅ etcd-server built (debug)
🚀 Starting etcd-server (Persistente)...
════════════════════════════════════════════════════════════
etcd-server Status:
63429 tmux new-session -d -s etcd-server mkdir -p /vagrant/logs/lab && cd /vagrant && sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/etcd-server/build-debug/etcd-server >> /vagrant/logs/lab/etcd-server.log 2>&1
63430 bash -c mkdir -p /vagrant/logs/lab && cd /vagrant && sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/etcd-server/build-debug/etcd-server >> /vagrant/logs/lab/etcd-server.log 2>&1
63433 sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/etcd-server/build-debug/etcd-server
63434 sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/etcd-server/build-debug/etcd-server
63435 /vagrant/etcd-server/build-debug/etcd-server
63454 bash -l -c pgrep -a -f etcd-server && echo '✅ etcd-server: RUNNING' || echo '❌ etcd-server: STOPPED'
✅ etcd-server: RUNNING
{"service":"etcd-server","status":"healthy","timestamp":1778044850}════════════════════════════════════════════════════════════
⏳ Waiting for etcd-server to stabilize (Seed generation)...
🚀 Starting rag-security (from /vagrant/rag/build-active)...
🚀 Starting RAG Ingester (Full Context)...
🧹 Limpiando SQLite lock anterior (si existe)...
Ejecución desde la raíz del componente para resolver paths relativos del config...
🚀 Starting ML Detector (Tricapa Persistente)...
🚀 Starting Firewall ACL (SUDO + TMUX)...
🚀 Starting Sniffer Variant A (eBPF/XDP)...
── [mutex] Verificando exclusion mutua Variant A/B ──
=== [sniffer-mutex] Verificando exclusion mutua (variant=ebpf) ===
[sniffer-mutex] Variant A (ebpf/tmux:sniffer):         inactive
[sniffer-mutex] Variant B (libpcap/tmux:sniffer-libpcap): inactive
[sniffer-mutex] OK — puede arrancar variant=ebpf

╔════════════════════════════════════════════════════════════╗
║  ✅ FULL PIPELINE STARTED (DAY 103 — con provisioning)     ║
╚════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════╗
║  📊 ML Defender Pipeline Status (via TMUX)                ║
╚════════════════════════════════════════════════════════════╝
✅ etcd-server:   RUNNING
✅ rag-security:  RUNNING
✅ rag-ingester:  RUNNING
✅ ml-detector:   RUNNING
✅ sniffer:       RUNNING
✅ firewall:      RUNNING
╚════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════╗
║  📊 ML Defender Pipeline Status (via TMUX)                ║
╚════════════════════════════════════════════════════════════╝
✅ etcd-server:   RUNNING
✅ rag-security:  RUNNING
✅ rag-ingester:  RUNNING
✅ ml-detector:   RUNNING
✅ sniffer:       RUNNING
✅ firewall:      RUNNING
╚════════════════════════════════════════════════════════════╝
TEST-INTEG-4a-PLUGIN: variantes A/B/C...

=== TEST VARIANT A ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Variant A: errors=0 result_code=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST VARIANT B ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Variant B: errors=1 → PASS (expect D8 VIOLATION log above)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST VARIANT C ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Variant C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4a-PLUGIN: PASSED (0 failures) ===
TEST-INTEG-4a PASSED
TEST-INTEG-4b: plugin READ-ONLY contract (rag-ingester PHASE 2b)...

=== TEST-INTEG-4b CASO A: READ-ONLY payload=nullptr ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=1 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4b CASO B: mode propagation ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso B: mode=1 (expect 1) → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4b: PASSED (0 failures) ===
TEST-INTEG-4b PASSED
TEST-INTEG-4c: plugin NORMAL contract (sniffer PHASE 2c)...

=== TEST-INTEG-4c CASO A: NORMAL + payload real ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4c CASO B: D8 VIOLATION campo read-only ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Caso B: errors=1 → D8 VIOLATION detectada → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4c CASO C: result_code=-1 no crash ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Caso C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4c: PASSED (0 failures) ===
TEST-INTEG-4c PASSED
TEST-INTEG-4d: plugin NORMAL contract (ml-detector PHASE 2d)...

=== TEST-INTEG-4d CASO A: NORMAL + score ML en annotation ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4d CASO B: D8 VIOLATION campo read-only ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Caso B: errors=1 → D8 VIOLATION detectada → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4d CASO C: result_code=-1 no crash ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Caso C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4d: PASSED (0 failures) ===
TEST-INTEG-4d PASSED
TEST-INTEG-4e: rag-security READONLY + ADR-029 D1-D5...

=== TEST-INTEG-4e CASO A: READONLY + evento real ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 mode=1 result_code ignorado → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4e CASO B: g_plugin_loader=nullptr, no crash ===
Caso B: g_plugin_loader=nullptr → invoke_all no llamado → PASS

=== TEST-INTEG-4e CASO C: simulacion signal handler → shutdown limpio ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[rag-security] signal received — shutting down
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=0 overruns=0 errors=0
Caso C: shutdown ejecutado, g_plugin_loader=nullptr → PASS

=== TEST-INTEG-4e: PASSED (0 failures) ===
TEST-INTEG-4e PASSED
TEST-INTEG-SIGN: Ed25519 plugin verification (ADR-025)...

=== TEST-INTEG-SIGN-1: firma valida → carga exitosa ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
SIGN-1: loaded_count=1 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=0 overruns=0 errors=0

=== TEST-INTEG-SIGN-2: firma invalida → loaded_count==0 ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-2: loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-3: .sig ausente → loaded_count==0 ===
[plugin-loader] CRITICAL: .sig not found for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-3: loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-4: symlink attack → loaded_count==0 ===
[plugin-loader] CRITICAL: cannot open plugin (symlink?): /usr/lib/ml-defender/plugins/libplugin_symlink_test.so
[plugin-loader] WARNING: 'test-sign-4' skipped (sig check failed, dev mode)
SIGN-4: symlink rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-5: path traversal → loaded_count==0 ===
[plugin-loader] CRITICAL: path outside allowed prefix: /usr/lib/ml-defender/plugins/../../../tmp/libplugin_test_message.so
[plugin-loader] WARNING: 'test-sign-5' skipped (sig check failed, dev mode)
SIGN-5: traversal rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-6: clave rotada → loaded_count==0 ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-6: key mismatch rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-7: plugin truncado → loaded_count==0 ===
[plugin-loader] CRITICAL: plugin size/type invalid: /usr/lib/ml-defender/plugins/libplugin_tiny_test.so
[plugin-loader] WARNING: 'test-sign-7' skipped (sig check failed, dev mode)
SIGN-7: tiny plugin rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN: PASSED (0 failures) ===
TEST-INTEG-SIGN PASSED
╔════════════════════════════════════════════════════════════╗
║  ✅ Bootstrap completado — 6/6 RUNNING                    ║
║  Siguiente: make test-all                                  ║
╚════════════════════════════════════════════════════════════╝
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker %
## make test-all
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % make test-all
Testing seed-client...
─── seed-client tests ───────────────────────
Test project /vagrant/libs/seed-client/build
Start 1: seed_client_tests
1/3 Test #1: seed_client_tests ................   Passed    0.04 sec
Start 2: perms_seed_tests
2/3 Test #2: perms_seed_tests .................   Passed    2.97 sec
Start 3: seed_client_traversal_tests
3/3 Test #3: seed_client_traversal_tests ......   Passed    0.07 sec

100% tests passed, 0 tests failed out of 3

Total Test time (real) =   3.18 sec
Testing crypto-transport...
Test project /vagrant/crypto-transport/build
Start 1: test_crypto
1/5 Test #1: test_crypto ......................   Passed    0.07 sec
Start 2: test_compression
2/5 Test #2: test_compression .................   Passed    0.06 sec
Start 3: test_integration
3/5 Test #3: test_integration .................   Passed    0.10 sec
Start 4: test_crypto_transport
4/5 Test #4: test_crypto_transport ............   Passed    0.13 sec
Start 5: test_integ_contexts
5/5 Test #5: test_integ_contexts ..............   Passed    0.06 sec

100% tests passed, 0 tests failed out of 5

Total Test time (real) =   0.56 sec
Testing etcd-client (HMAC only)...
═══════════════════════════════════════════════════════════
EtcdClient HMAC Utilities - Unit Tests
═══════════════════════════════════════════════════════════

✅ PASS: test_bytes_to_hex
✅ PASS: test_hex_to_bytes
✅ PASS: test_hex_roundtrip
✅ PASS: test_invalid_hex
✅ PASS: test_empty_conversions
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_consistency
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_different_data
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_different_keys
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_validation_valid
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_validation_invalid
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_validation_tampered
⚠️  [etcd-client] component_config_path vacío — CryptoTransport no inicializado
🔧 EtcdClient initialized (no crypto): test
✅ PASS: test_hmac_length

═══════════════════════════════════════════════════════════
Results: 12/12 tests passed
═══════════════════════════════════════════════════════════
🎉 ALL TESTS PASSED!
Testing plugin-loader...
Testing safe-path property tests...
Running main() from ./googletest/src/gtest_main.cc
[==========] Running 5 tests from 1 test suite.
[----------] Global test environment set-up.
[----------] 5 tests from SafePathPropertyTest
[ RUN      ] SafePathPropertyTest.ResolveSeedNeverEscapesPrefix
[       OK ] SafePathPropertyTest.ResolveSeedNeverEscapesPrefix (8 ms)
[ RUN      ] SafePathPropertyTest.ResolveSeedNeverAcceptsSymlinks
[       OK ] SafePathPropertyTest.ResolveSeedNeverAcceptsSymlinks (0 ms)
[ RUN      ] SafePathPropertyTest.ResolveConfigNeverEscapesPrefixLexical
[       OK ] SafePathPropertyTest.ResolveConfigNeverEscapesPrefixLexical (1 ms)
[ RUN      ] SafePathPropertyTest.ResolveConfigAcceptsSymlinksInsidePrefix
[       OK ] SafePathPropertyTest.ResolveConfigAcceptsSymlinksInsidePrefix (1 ms)
[ RUN      ] SafePathPropertyTest.ResolveGeneralPrefixNeverDerivesFromInput
[       OK ] SafePathPropertyTest.ResolveGeneralPrefixNeverDerivesFromInput (1 ms)
[----------] 5 tests from SafePathPropertyTest (18 ms total)

[----------] Global test environment tear-down
[==========] 5 tests from 1 test suite ran. (19 ms total)
[  PASSED  ] 5 tests.

🧪 Testing plugin-loader...
Test project /vagrant/plugin-loader/build
No tests were found!!!
TEST-INTEG-4a-PLUGIN: variantes A/B/C...

=== TEST VARIANT A ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Variant A: errors=0 result_code=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST VARIANT B ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Variant B: errors=1 → PASS (expect D8 VIOLATION log above)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST VARIANT C ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Variant C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4a-PLUGIN: PASSED (0 failures) ===
TEST-INTEG-4a PASSED
TEST-INTEG-4b: plugin READ-ONLY contract (rag-ingester PHASE 2b)...

=== TEST-INTEG-4b CASO A: READ-ONLY payload=nullptr ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=1 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4b CASO B: mode propagation ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso B: mode=1 (expect 1) → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4b: PASSED (0 failures) ===
TEST-INTEG-4b PASSED
TEST-INTEG-4c: plugin NORMAL contract (sniffer PHASE 2c)...

=== TEST-INTEG-4c CASO A: NORMAL + payload real ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4c CASO B: D8 VIOLATION campo read-only ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Caso B: errors=1 → D8 VIOLATION detectada → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4c CASO C: result_code=-1 no crash ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Caso C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4c: PASSED (0 failures) ===
TEST-INTEG-4c PASSED
TEST-INTEG-4d: plugin NORMAL contract (ml-detector PHASE 2d)...

=== TEST-INTEG-4d CASO A: NORMAL + score ML en annotation ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4d CASO B: D8 VIOLATION campo read-only ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Caso B: errors=1 → D8 VIOLATION detectada → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4d CASO C: result_code=-1 no crash ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Caso C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4d: PASSED (0 failures) ===
TEST-INTEG-4d PASSED
TEST-INTEG-4e: rag-security READONLY + ADR-029 D1-D5...

=== TEST-INTEG-4e CASO A: READONLY + evento real ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 mode=1 result_code ignorado → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4e CASO B: g_plugin_loader=nullptr, no crash ===
Caso B: g_plugin_loader=nullptr → invoke_all no llamado → PASS

=== TEST-INTEG-4e CASO C: simulacion signal handler → shutdown limpio ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[rag-security] signal received — shutting down
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=0 overruns=0 errors=0
Caso C: shutdown ejecutado, g_plugin_loader=nullptr → PASS

=== TEST-INTEG-4e: PASSED (0 failures) ===
TEST-INTEG-4e PASSED
TEST-INTEG-SIGN: Ed25519 plugin verification (ADR-025)...

=== TEST-INTEG-SIGN-1: firma valida → carga exitosa ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
SIGN-1: loaded_count=1 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=0 overruns=0 errors=0

=== TEST-INTEG-SIGN-2: firma invalida → loaded_count==0 ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-2: loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-3: .sig ausente → loaded_count==0 ===
[plugin-loader] CRITICAL: .sig not found for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-3: loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-4: symlink attack → loaded_count==0 ===
[plugin-loader] CRITICAL: cannot open plugin (symlink?): /usr/lib/ml-defender/plugins/libplugin_symlink_test.so
[plugin-loader] WARNING: 'test-sign-4' skipped (sig check failed, dev mode)
SIGN-4: symlink rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-5: path traversal → loaded_count==0 ===
[plugin-loader] CRITICAL: path outside allowed prefix: /usr/lib/ml-defender/plugins/../../../tmp/libplugin_test_message.so
[plugin-loader] WARNING: 'test-sign-5' skipped (sig check failed, dev mode)
SIGN-5: traversal rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-6: clave rotada → loaded_count==0 ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-6: key mismatch rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-7: plugin truncado → loaded_count==0 ===
[plugin-loader] CRITICAL: plugin size/type invalid: /usr/lib/ml-defender/plugins/libplugin_tiny_test.so
[plugin-loader] WARNING: 'test-sign-7' skipped (sig check failed, dev mode)
SIGN-7: tiny plugin rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN: PASSED (0 failures) ===
TEST-INTEG-SIGN PASSED

╔════════════════════════════════════════════════════════════╗
║  🧪 Running Component Tests [debug]                  ║
╚════════════════════════════════════════════════════════════╝

Testing Sniffer...
Test project /vagrant/sniffer/build-debug
Start 1: test_smb_scan_features
1/9 Test #1: test_smb_scan_features ...........   Passed    0.09 sec
Start 2: test_pcap_backend_lifecycle
2/9 Test #2: test_pcap_backend_lifecycle ......   Passed    0.05 sec
Start 3: test_pcap_backend_poll_null
3/9 Test #3: test_pcap_backend_poll_null ......   Passed    0.08 sec
Start 4: test_pcap_backend_callback
4/9 Test #4: test_pcap_backend_callback .......   Passed    0.06 sec
Start 5: test_pcap_backend_error
5/9 Test #5: test_pcap_backend_error ..........   Passed    0.07 sec
Start 6: test_pcap_proto_parse_tcp
6/9 Test #6: test_pcap_proto_parse_tcp ........   Passed    0.03 sec
Start 7: test_pcap_proto_parse_udp
7/9 Test #7: test_pcap_proto_parse_udp ........   Passed    0.03 sec
Start 8: test_pcap_backend_stress
8/9 Test #8: test_pcap_backend_stress .........   Passed    0.09 sec
Start 9: test_pcap_backend_regression
9/9 Test #9: test_pcap_backend_regression .....   Passed    0.05 sec

100% tests passed, 0 tests failed out of 9

Total Test time (real) =   0.70 sec

Testing ML Detector...
Test project /vagrant/ml-detector/build-debug
Start  1: test_classifier
1/10 Test  #1: test_classifier ..................   Passed    0.03 sec
Start  2: test_feature_extractor
2/10 Test  #2: test_feature_extractor ...........   Passed    0.04 sec
Start  3: test_rag_logger_artifact_save
3/10 Test  #3: test_rag_logger_artifact_save ....   Passed    0.04 sec
Start  4: test_model_loader
4/10 Test  #4: test_model_loader ................   Passed    0.05 sec
Start  5: test_zmq_memory_overflow
5/10 Test  #5: test_zmq_memory_overflow .........   Passed    0.06 sec
Start  6: RansomwareDetectorUnit
6/10 Test  #6: RansomwareDetectorUnit ...........   Passed    0.17 sec
Start  7: test_pipeline
7/10 Test  #7: test_pipeline ....................   Passed    0.06 sec
Start  8: test_csv_event_writer
8/10 Test  #8: test_csv_event_writer ............   Passed    0.09 sec
Start  9: test_csv_feature_extraction
9/10 Test  #9: test_csv_feature_extraction ......   Passed    0.06 sec
Start 10: test_etcd_client_hmac
10/10 Test #10: test_etcd_client_hmac ............   Passed   12.42 sec

100% tests passed, 0 tests failed out of 10

Total Test time (real) =  13.23 sec

Testing RAG Ingester...
Test project /vagrant/rag-ingester/build-debug
Start 1: test_config_parser
1/8 Test #1: test_config_parser ...............   Passed    0.06 sec
Start 2: test_config_parser_traversal
2/8 Test #2: test_config_parser_traversal .....   Passed    0.09 sec
Start 3: test_file_watcher
3/8 Test #3: test_file_watcher ................   Passed    1.07 sec
Start 4: test_csv_file_watcher
4/8 Test #4: test_csv_file_watcher ............   Passed    1.99 sec
Start 5: test_csv_event_loader
5/8 Test #5: test_csv_event_loader ............   Passed    0.04 sec
Start 6: test_csv_dir_watcher
6/8 Test #6: test_csv_dir_watcher .............   Passed    0.64 sec
Start 7: test_firewall_csv_event_loader
7/8 Test #7: test_firewall_csv_event_loader ...   Passed    0.04 sec
Start 8: test_trace_id
8/8 Test #8: test_trace_id ....................   Passed    0.07 sec

100% tests passed, 0 tests failed out of 8

Total Test time (real) =   4.13 sec

Testing etcd-server...
Test project /vagrant/etcd-server/build-debug
Start 1: test_hmac_integration
1/2 Test #1: test_hmac_integration ............   Passed    0.16 sec
Start 2: test_secrets_manager_simple
2/2 Test #2: test_secrets_manager_simple ......   Passed    9.49 sec

100% tests passed, 0 tests failed out of 2

Total Test time (real) =   9.86 sec

Testing RAG Security...
Test project /vagrant/rag/build
No tests were found!!!


╔════════════════════════════════════════════════════════════╗
║  🔍 TEST-PROVISION-1 — CI Gate PHASE 3                   ║
╚════════════════════════════════════════════════════════════╝

── Check 1/8: Claves criptográficas ──

══ Verificación de integridad ══
✅ etcd-server: OK
✅ sniffer: OK
✅ ml-detector: OK
✅ firewall-acl-agent: OK
✅ rag-ingester: OK
✅ rag-security: OK

✅ Todas las claves verificadas correctamente
✅ Check 1/8 OK

── Check 2/8: Firmas de plugins (producción) ──

══ check-plugins (DEBT-SIGN-AUTO, ADR-025) ══
→ Modo: PRODUCCIÓN — solo verificar, nunca firmar
→ libplugin_test_message.so: .sig válido — skip
→ libplugin_xgboost.so: .sig válido — skip

✅ 2 plugin(s) ya firmados y válidos (skip)
✅ check-plugins completado — todos los plugins firmados y verificados
✅ Check 2/8 OK

── Check 3/8: Configs de producción (sin dev plugins) ──
🔍 Validando que libplugin_hello NO está en configs de producción...
✅ validate-prod-configs: libplugin_hello ausente en todos los configs
✅ Check 3/8 OK

── Check 4/8: build-active symlinks ──
✅ Check 4/8 OK

── Check 5/8: systemd units instalados ──
✅ Check 5/8 OK


── Check 6/8: Permisos ficheros sensibles ──
✅ Check 6/8 OK

── Check 7/8: Consistencia JSONs con plugins reales ──
✅ Sin plugins activos en configs de producción (correcto)
✅ Check 7/8 OK

── Check 8/8: apparmor-utils instalado ──
✅ Check 8/8 OK
╔════════════════════════════════════════════════════════════╗
║  ✅ TEST-PROVISION-1 PASSED — entorno listo               ║
╚════════════════════════════════════════════════════════════╝


── TEST-INVARIANT-SEED: 6 seeds idénticos post-reset ──
Hashes únicos: 1
✅ TEST-INVARIANT-SEED PASSED

TEST-INTEG-4a-PLUGIN: variantes A/B/C...

=== TEST VARIANT A ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Variant A: errors=0 result_code=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST VARIANT B ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Variant B: errors=1 → PASS (expect D8 VIOLATION log above)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST VARIANT C ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Variant C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4a-PLUGIN: PASSED (0 failures) ===
TEST-INTEG-4a PASSED
TEST-INTEG-4b: plugin READ-ONLY contract (rag-ingester PHASE 2b)...

=== TEST-INTEG-4b CASO A: READ-ONLY payload=nullptr ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=1 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4b CASO B: mode propagation ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso B: mode=1 (expect 1) → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4b: PASSED (0 failures) ===
TEST-INTEG-4b PASSED
TEST-INTEG-4c: plugin NORMAL contract (sniffer PHASE 2c)...

=== TEST-INTEG-4c CASO A: NORMAL + payload real ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4c CASO B: D8 VIOLATION campo read-only ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Caso B: errors=1 → D8 VIOLATION detectada → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4c CASO C: result_code=-1 no crash ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Caso C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4c: PASSED (0 failures) ===
TEST-INTEG-4c PASSED
TEST-INTEG-4d: plugin NORMAL contract (ml-detector PHASE 2d)...

=== TEST-INTEG-4d CASO A: NORMAL + score ML en annotation ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 result_code=0 mode=0 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4d CASO B: D8 VIOLATION campo read-only ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=B
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only en MessageContext — D8 VIOLATION
Caso B: errors=1 → D8 VIOLATION detectada → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4d CASO C: result_code=-1 no crash ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=C
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant C: returning result_code=-1 (anomaly)
[plugin-loader] WARNING: plugin 'test-message' returned PLUGIN_ERROR en MessageContext
Caso C: errors=1 → PASS (no crash = OK)
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=1

=== TEST-INTEG-4d: PASSED (0 failures) ===
TEST-INTEG-4d PASSED
TEST-INTEG-4e: rag-security READONLY + ADR-029 D1-D5...

=== TEST-INTEG-4e CASO A: READONLY + evento real ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[test-message] variant A: OK
Caso A: errors=0 mode=1 result_code ignorado → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=1 overruns=0 errors=0

=== TEST-INTEG-4e CASO B: g_plugin_loader=nullptr, no crash ===
Caso B: g_plugin_loader=nullptr → invoke_all no llamado → PASS

=== TEST-INTEG-4e CASO C: simulacion signal handler → shutdown limpio ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
[rag-security] signal received — shutting down
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=0 overruns=0 errors=0
Caso C: shutdown ejecutado, g_plugin_loader=nullptr → PASS

=== TEST-INTEG-4e: PASSED (0 failures) ===
TEST-INTEG-4e PASSED
TEST-INTEG-SIGN: Ed25519 plugin verification (ADR-025)...

=== TEST-INTEG-SIGN-1: firma valida → carga exitosa ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] INFO: 'test-message' signature OK
[test-message] plugin_init: variant=A
[plugin-loader] INFO: loaded plugin 'test-message' v0.1.0
SIGN-1: loaded_count=1 → PASS
[test-message] plugin_shutdown
[plugin-loader] INFO: shutdown plugin 'test-message' — invocations=0 overruns=0 errors=0

=== TEST-INTEG-SIGN-2: firma invalida → loaded_count==0 ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-2: loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-3: .sig ausente → loaded_count==0 ===
[plugin-loader] CRITICAL: .sig not found for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-3: loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-4: symlink attack → loaded_count==0 ===
[plugin-loader] CRITICAL: cannot open plugin (symlink?): /usr/lib/ml-defender/plugins/libplugin_symlink_test.so
[plugin-loader] WARNING: 'test-sign-4' skipped (sig check failed, dev mode)
SIGN-4: symlink rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-5: path traversal → loaded_count==0 ===
[plugin-loader] CRITICAL: path outside allowed prefix: /usr/lib/ml-defender/plugins/../../../tmp/libplugin_test_message.so
[plugin-loader] WARNING: 'test-sign-5' skipped (sig check failed, dev mode)
SIGN-5: traversal rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-6: clave rotada → loaded_count==0 ===
[plugin-loader] INFO: 'test-message' SHA-256=1a13623f603305b75f9753f52d691af1b2308ae7a89fe31894f67d1a813449b8 size=15800 mtime=1778044411
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
[plugin-loader] WARNING: 'test-message' skipped (sig check failed, dev mode)
SIGN-6: key mismatch rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN-7: plugin truncado → loaded_count==0 ===
[plugin-loader] CRITICAL: plugin size/type invalid: /usr/lib/ml-defender/plugins/libplugin_tiny_test.so
[plugin-loader] WARNING: 'test-sign-7' skipped (sig check failed, dev mode)
SIGN-7: tiny plugin rejected, loaded_count=0 (expect 0) → PASS

=== TEST-INTEG-SIGN: PASSED (0 failures) ===
TEST-INTEG-SIGN PASSED

╔════════════════════════════════════════════════════════════╗
║  ✅ ALL TESTS COMPLETE                                    ║
╚════════════════════════════════════════════════════════════╝

(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % 

