#!/usr/bin/perl
# DAY339 — DEBT-SNIFFER-IS-EXTERNAL-IP-BYTE-ORDER-001, medida 4: las filas argus invertidas, sin filtrar por col 6.
# La v2 las metió en el "día 0" (int(col6/86400)=0) y la v3 (col6 eq "0") no encontró ninguna: col6 es otra cosa.
#   R = dst_ip x.x.168.192   S = 251.0.x.x, 255.56.x.x, x.x.0.224, x.x.56.255 (y no 192.168)
# Por grupo: valores de col 6 tal cual (top 10), fecha de modificación UTC de sus ficheros, número de ficheros,
# primer y último fichero, y la primera fila vista (col 18, el HMAC, recortada a 8 caracteres).
# Uso (Mac, raíz del repo): perl scripts/etcd_ha/d339_medir_orden_dst_ip_v4.pl logs/correlation
# Solo lee.
use strict; use warnings; use File::Find; use POSIX qw(strftime);
my $dir = shift or die "falta el directorio del bronce\n";
-d $dir or die "no existe: $dir\n";
my (%c6, %dia, %fich, %prim, %ult, %muestra, %tot);
find({ no_chdir => 1, wanted => sub {
  return unless -f $_ && !/\.gz$/;
  my $f = $_; my $m = (stat $f)[9];
  open(my $h, '<', $f) or do { warn "no se puede leer $f\n"; return };
  while (my $l = <$h>) {
    chomp $l; my @x = split /,/, $l, -1;
    next unless @x == 19 && $x[1] eq 'argus';
    my @o = split /\./, $x[8]; next unless @o == 4;
    next if $o[0]==192 && $o[1]==168;
    my $k = ($o[3]==192 && $o[2]==168) ? 'R'
          : (($o[0]==251 && $o[1]==0) || ($o[0]==255 && $o[1]==56) || ($o[3]==224 && $o[2]==0) || ($o[3]==255 && $o[2]==56)) ? 'S'
          : next;
    $tot{$k}++;
    $c6{$k}{"[$x[5]]"}++;
    $dia{$k}{strftime('%Y-%m-%d', gmtime $m)}++;
    $fich{$k}{$f} = 1;
    $prim{$k} = [$m, $f] if !$prim{$k} || $m < $prim{$k}[0];
    $ult{$k}  = [$m, $f] if !$ult{$k}  || $m > $ult{$k}[0];
    if (!$muestra{$k}) { $x[18] = substr($x[18], 0, 8) . '...'; $muestra{$k} = join(',', @x) }
  }
  close $h;
}}, $dir);
for my $k (qw(R S)) {
  printf "== %s: filas %d, ficheros %d\n", $k, $tot{$k} // 0, scalar keys %{ $fich{$k} // {} };
  next unless $tot{$k};
  my $h = $c6{$k}; my @v = sort { $h->{$b} <=> $h->{$a} || $a cmp $b } keys %$h;
  printf "%s col6 distintos: %d; top 10 (filas valor):\n", $k, scalar @v;
  printf "  %d %s\n", $h->{$_}, $_ for @v[0 .. ($#v < 9 ? $#v : 9)];
  print "$k por fecha_mtime (fecha filas):\n";
  printf "  %s %d\n", $_, $dia{$k}{$_} for sort keys %{ $dia{$k} };
  printf "%s primero: %s %s\n", $k, strftime('%Y-%m-%dT%H:%M:%SZ', gmtime $prim{$k}[0]), $prim{$k}[1];
  printf "%s ultimo:  %s %s\n", $k, strftime('%Y-%m-%dT%H:%M:%SZ', gmtime $ult{$k}[0]),  $ult{$k}[1];
  print "$k muestra: $muestra{$k}\n";
}
