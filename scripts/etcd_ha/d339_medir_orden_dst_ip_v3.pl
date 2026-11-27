#!/usr/bin/perl
# DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001, medida 3: filas argus con flow_start_sec = 0
# (col 6; las fast-alerts hasta ad0e0ada, 13-oct) fechadas por la fecha de modificación (UTC) del fichero.
#   N = dst_ip 192.168.x.x   R = x.x.168.192   S = 251.0.x.x, 255.56.x.x, x.x.0.224, x.x.56.255   O = resto
# Y, para R y S, el primer y el último fichero (por fecha) donde aparecen.
# Uso (Mac, raíz del repo): perl scripts/etcd_ha/d339_medir_orden_dst_ip_v3.pl logs/correlation
# Solo lee.
use strict; use warnings; use File::Find; use POSIX qw(strftime);
my $dir = shift or die "falta el directorio del bronce\n";
-d $dir or die "no existe: $dir\n";
my (%c, %prim, %ult, $fich);
find({ no_chdir => 1, wanted => sub {
  return unless -f $_ && !/\.gz$/;
  my $f = $_; my $m = (stat $f)[9];
  my $dia = strftime('%Y-%m-%d', gmtime $m);
  open(my $h, '<', $f) or do { warn "no se puede leer $f\n"; return };
  $fich++;
  while (my $l = <$h>) {
    chomp $l; my @x = split /,/, $l, -1;
    next unless @x == 19 && $x[1] eq 'argus' && $x[5] eq '0';
    my @o = split /\./, $x[8]; next unless @o == 4;
    my $k = ($o[0]==192 && $o[1]==168) ? 'N'
          : ($o[3]==192 && $o[2]==168) ? 'R'
          : (($o[0]==251 && $o[1]==0) || ($o[0]==255 && $o[1]==56) || ($o[3]==224 && $o[2]==0) || ($o[3]==255 && $o[2]==56)) ? 'S'
          : 'O';
    $c{$dia}{$k}++;
    if ($k eq 'R' || $k eq 'S') {
      $prim{$k} = [$m, $f] if !$prim{$k} || $m < $prim{$k}[0];
      $ult{$k}  = [$m, $f] if !$ult{$k}  || $m > $ult{$k}[0];
    }
  }
  close $h;
}}, $dir);
print "ficheros leidos: ", ($fich // 0), "\n";
print "== fecha_mtime N R S O (filas argus con flow_start_sec=0)\n";
for my $d (sort keys %c) { printf "%s %d %d %d %d\n", $d, map { $c{$d}{$_} // 0 } qw(N R S O) }
for my $k (qw(R S)) {
  next unless $prim{$k};
  printf "%s primero: %s %s\n", $k, strftime('%Y-%m-%dT%H:%M:%SZ', gmtime $prim{$k}[0]), $prim{$k}[1];
  printf "%s ultimo:  %s %s\n", $k, strftime('%Y-%m-%dT%H:%M:%SZ', gmtime $ult{$k}[0]),  $ult{$k}[1];
}
