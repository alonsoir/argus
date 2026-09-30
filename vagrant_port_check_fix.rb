# DAY284 — workaround: desde la actualizacion de macOS del 2026-09-30 (medido en 15.8.1;
# el issue lo reporta en 26.7+) un connect no bloqueante rechazado deja el socket "escribible"
# con el error en SO_ERROR. Socket.tcp(connect_timeout:) lo toma por exito y devuelve un socket
# muerto -> Vagrant 2.4.9 ve TODOS los puertos ocupados (ForwardPortCollision falso).
# Refs: hashicorp/vagrant#13845, PR #13842, Ruby Bug #22223.
# Solo se activa si el sondeo detecta el falso positivo; con Vagrant/macOS arreglado no hace nada.
# Quitar cuando Vagrant publique el fix (DEBT-VAGRANT-PORT-CHECK-MACOS-001).
require "socket"
require "vagrant/util/is_port_open"

module ArgusPortCheckFix
  def self.falso_positivo?
    probe = TCPServer.new("127.0.0.1", 0)
    libre = probe.addr[1]
    probe.close
    Socket.tcp("127.0.0.1", libre, connect_timeout: 0.1).close
    true
  rescue StandardError
    false
  end
end

if ArgusPortCheckFix.falso_positivo?
  module Vagrant
    module Util
      module IsPortOpen
        def is_port_open?(host, port)
          sock = Socket.tcp(host, port, connect_timeout: 0.1)
          begin
            err = sock.getsockopt(Socket::SOL_SOCKET, Socket::SO_ERROR).int
            sock.remote_address          # socket muerto -> ENOTCONN / EINVAL
            err == 0
          ensure
            sock.close
          end
        rescue Errno::ETIMEDOUT, Errno::ECONNREFUSED, Errno::EHOSTUNREACH,
               Errno::ENETUNREACH, Errno::EACCES, Errno::ENOTCONN, Errno::EALREADY,
               Errno::EINVAL
          false
        end
      end
    end
  end
  $stderr.puts "[argus] port-check fix ACTIVO (socket muerto en connect rechazado / vagrant#13845)"
end
