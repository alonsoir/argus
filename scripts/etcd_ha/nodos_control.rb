# nodos_control.rb — DAY324, PR2b paso 2 de DEBT-ETCD-HA-TLS-RAFT-001 [PLANO-CONTROL-D324]. La lista de nodos del plano
# de control del laboratorio (etcd + Vault + etcd-server, ADR-048/049 revisión DAY324) sale de UN sitio: el group_vars
# del inventario (ansible/inventory/group_vars/argus_dev.yml), el mismo que ya da argus_hospital_id. La leen el
# Vagrantfile (require) y el test (ruby nodos_control.rb ...): una sola validación para los dos.
# Vagrant es el despliegue de DESARROLLO; en producción el inventario lo lee Ansible/Jenkins, que tendrá la suya.
#
# Campos (todos obligatorios: sin valor sano por defecto, como el hospital; un error = no se levanta nada):
#   argus_control_nodos: lista de 1 a 7 nodos {nombre, ip, mac}. Con un número par se avisa (Raft no gana tolerancia).
#     nombre  [a-z0-9-], de 1 a 32, sin repetir. El PRIMERO es control-1 en 192.168.100.20: el resto del laboratorio
#             (Makefile, scripts, manifiesto de protegidos, firewall del defender) lo da por hecho hasta el PR2d.
#     ip      192.168.100.N con N en [2, 254], sin repetir, y ninguna de las que ya usan otras VMs del Vagrantfile.
#     mac     12 hexadecimales en mayúsculas que empiezan por 080027 (OUI de VirtualBox), sin repetir. Fija: el
#             manifiesto de protegidos ata cada IP de infraestructura a su MAC (ADR-060, antispoofing).
#   argus_control_memoria_mb: entero [768, 4096] (DAY324: los servicios de un nodo suman ~510 MB de pico).
#   argus_control_cpus: entero [1, 4].
# Uso desde la terminal (raíz del repo):
#   ruby scripts/etcd_ha/nodos_control.rb nodos GROUP_VARS VAGRANTFILE   -> TSV: nodo<TAB>nombre<TAB>ip<TAB>mac, memoria_mb, cpus
#   ruby scripts/etcd_ha/nodos_control.rb inventario INVENTARIO          -> host<TAB>ansible_host de argus_dev, uno por línea
#   ruby scripts/etcd_ha/nodos_control.rb grupo INVENTARIO GRUPO         -> los hosts del grupo, uno por línea
#   ruby scripts/etcd_ha/nodos_control.rb nombres GROUP_VARS VAGRANTFILE -> los nombres en una línea (el Makefile: CONTROL_NODOS)
# rc 0 si todo vale; rc 1 con un error por línea (campo, valor, formato y límites).
require "yaml"

module ArgusNodosControl
  RED = "192.168.100."
  PRIMERO = { "nombre" => "control-1", "ip" => "192.168.100.20" }.freeze

  # IPs que ya usan otras VMs: las literales ip: "..." del Vagrantfile (las de los nodos de control no son literales)
  def self.ocupadas(vagrantfile)
    File.read(vagrantfile, encoding: "UTF-8").scan(/\bip:\s*"(\d+\.\d+\.\d+\.\d+)"/).flatten.uniq
  end

  def self.entero(d, campo, lo, hi, errores)
    v = d[campo]
    unless v.is_a?(Integer) && v >= lo && v <= hi
      errores << "#{campo}=#{v.inspect}: entero en [#{lo}, #{hi}]"
      return nil
    end
    v
  end

  # Devuelve [config, errores, avisos]; config = {"nodos" => [...], "memoria_mb" => N, "cpus" => N}
  def self.cargar(group_vars, vagrantfile)
    errores = []
    avisos = []
    begin
      d = YAML.safe_load(File.read(group_vars, encoding: "UTF-8")) || {}
    rescue StandardError => e
      return [nil, ["#{group_vars}: no se puede leer como YAML (#{e.class}: #{e.message})"], avisos]
    end
    return [nil, ["#{group_vars}: no es un mapa YAML"], avisos] unless d.is_a?(Hash)
    lista = d["argus_control_nodos"]
    unless lista.is_a?(Array) && lista.size >= 1 && lista.size <= 7
      errores << "argus_control_nodos: lista de 1 a 7 nodos {nombre, ip, mac} " \
                 "(hay #{lista.is_a?(Array) ? lista.size : lista.inspect})"
      lista = []
    end
    ocup = ocupadas(vagrantfile)
    vistos = { "nombre" => {}, "ip" => {}, "mac" => {} }
    nodos = []
    lista.each_with_index do |n, i|
      p = "argus_control_nodos[#{i}]"
      unless n.is_a?(Hash)
        errores << "#{p}: tiene que ser {nombre, ip, mac}, no #{n.inspect}"
        next
      end
      nombre, ip, mac = n["nombre"].to_s, n["ip"].to_s, n["mac"].to_s
      errores << "#{p}.nombre=#{n["nombre"].inspect}: [a-z0-9-], de 1 a 32" unless nombre.match?(/\A[a-z0-9-]{1,32}\z/)
      oct = ip[/\A192\.168\.100\.(\d{1,3})\z/, 1]
      unless oct && oct.to_i >= 2 && oct.to_i <= 254
        errores << "#{p}.ip=#{n["ip"].inspect}: 192.168.100.N con N en [2, 254]"
      end
      errores << "#{p}.ip=#{ip}: ya la usa otra VM del Vagrantfile (#{ocup.join(", ")})" if ocup.include?(ip)
      unless mac.match?(/\A080027[0-9A-F]{6}\z/)
        errores << "#{p}.mac=#{n["mac"].inspect}: 12 hexadecimales en mayúsculas que empiezan por 080027"
      end
      { "nombre" => nombre, "ip" => ip, "mac" => mac }.each do |k, v|
        if vistos[k].key?(v)
          errores << "#{p}.#{k}=#{v}: repetido (también en argus_control_nodos[#{vistos[k][v]}])"
        else
          vistos[k][v] = i
        end
      end
      nodos << { "nombre" => nombre, "ip" => ip, "mac" => mac }
    end
    if nodos.any? && (nodos[0]["nombre"] != PRIMERO["nombre"] || nodos[0]["ip"] != PRIMERO["ip"])
      errores << "argus_control_nodos[0]: tiene que ser #{PRIMERO["nombre"]} en #{PRIMERO["ip"]} " \
                 "(es #{nodos[0]["nombre"]} en #{nodos[0]["ip"]}); el resto del laboratorio lo da por hecho"
    end
    avisos << "argus_control_nodos: #{nodos.size} nodos, número par: Raft tolera los mismos fallos que con #{nodos.size - 1}" if nodos.size.even?
    mem = entero(d, "argus_control_memoria_mb", 768, 4096, errores)
    cpus = entero(d, "argus_control_cpus", 1, 4, errores)
    return [nil, errores, avisos] unless errores.empty?
    [{ "nodos" => nodos, "memoria_mb" => mem, "cpus" => cpus }, errores, avisos]
  end

  def self.hosts_inventario(inventario)
    d = YAML.safe_load(File.read(inventario, encoding: "UTF-8")) || {}
    h = (((d["all"] || {})["children"] || {})["argus_dev"] || {})["hosts"] || {}
    h.map { |nombre, v| [nombre, (v || {})["ansible_host"].to_s] }
  end

  def self.hosts_grupo(inventario, grupo)
    d = YAML.safe_load(File.read(inventario, encoding: "UTF-8")) || {}
    ((((d["all"] || {})["children"] || {})[grupo] || {})["hosts"] || {}).keys
  end
end

if $PROGRAM_NAME == __FILE__
  modo = ARGV[0]
  case modo
  when "nodos"
    abort "uso: ruby #{$PROGRAM_NAME} nodos GROUP_VARS VAGRANTFILE" unless ARGV.size == 3
    cfg, errores, avisos = ArgusNodosControl.cargar(ARGV[1], ARGV[2])
    avisos.each { |a| warn "[PLANO-CONTROL] AVISO #{a}" }
    unless errores.empty?
      errores.each { |e| puts "[PLANO-CONTROL] ERROR #{e}" }
      exit 1
    end
    cfg["nodos"].each { |n| puts ["nodo", n["nombre"], n["ip"], n["mac"]].join("\t") }
    puts "memoria_mb\t#{cfg["memoria_mb"]}"
    puts "cpus\t#{cfg["cpus"]}"
  when "nombres"
    abort "uso: ruby #{$PROGRAM_NAME} nombres GROUP_VARS VAGRANTFILE" unless ARGV.size == 3
    cfg, errores, avisos = ArgusNodosControl.cargar(ARGV[1], ARGV[2])
    avisos.each { |a| warn "[PLANO-CONTROL] AVISO #{a}" }
    unless errores.empty?
      errores.each { |e| warn "[PLANO-CONTROL] ERROR #{e}" }
      exit 1
    end
    puts cfg["nodos"].map { |n| n["nombre"] }.join(" ")
  when "grupo"
    abort "uso: ruby #{$PROGRAM_NAME} grupo INVENTARIO GRUPO" unless ARGV.size == 3
    puts ArgusNodosControl.hosts_grupo(ARGV[1], ARGV[2])
  when "inventario"
    abort "uso: ruby #{$PROGRAM_NAME} inventario INVENTARIO" unless ARGV.size == 2
    ArgusNodosControl.hosts_inventario(ARGV[1]).each { |n, ip| puts "#{n}\t#{ip}" }
  else
    abort "uso: ruby #{$PROGRAM_NAME} nodos|nombres GROUP_VARS VAGRANTFILE | inventario INVENTARIO | grupo INVENTARIO GRUPO"
  end
end
