#!/usr/bin/perl
# [KERNEL-HOMOGENEO-D329] (anfitrión) con_limite.pl <segundos> <orden> [args...]: ejecuta la orden con tiempo límite.
# La orden va en su propio grupo de procesos y, si vence el límite, se mata el GRUPO entero (TERM y, a los 2 s, KILL) y
# sale con 142. Un alarm sobre vagrant solo no basta: su ssh hijo sigue vivo con la salida abierta y quien lee esa
# salida se queda esperando (medido DAY329 en test_kernel_homogeneo.sh: 61 s con un límite de 10). Sin la orden: 127.
# Si la orden muere por una señal: 128 + señal; si no, su código de salida.
use strict;
use warnings;
my $lim = shift @ARGV;
die "uso: con_limite.pl <segundos> <orden> [args...]\n" unless defined $lim && $lim =~ /\A[1-9][0-9]*\z/ && @ARGV;
my $pid = fork();
die "con_limite.pl: fork: $!\n" unless defined $pid;
if ($pid == 0) {
  setpgrp(0, 0);
  exec { $ARGV[0] } @ARGV;
  exit 127;
}
$SIG{ALRM} = sub {
  kill 'TERM', -$pid;
  sleep 2;
  kill 'KILL', -$pid;
  waitpid($pid, 0);
  exit 142;
};
alarm $lim;
waitpid($pid, 0);
alarm 0;
my $st = $?;
exit(($st & 127) ? 128 + ($st & 127) : $st >> 8);
