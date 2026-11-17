# frozen_string_literal: true
# [DEBIAN-FECHA-D329] tests de lab_comun.rb (anfitrión; sin gemas: biblioteca estándar y un directorio temporal).
# Cada caso comprueba el valor Y que el error o el aviso salen, para que un validador que lo aceptara todo falle aquí.
require "tmpdir"
require_relative "lab_comun"

AHORA = Time.utc(2026, 11, 17, 6, 0, 0)
$fallos = 0
$casos = 0

def caso(nombre, contenido)
  Dir.mktmpdir do |d|
    ruta = File.join(d, "all.yml")
    File.write(ruta, contenido)
    r = ArgusLabComun.cargar(ruta, AHORA)
    ok = yield(*r)
    $casos += 1
    $fallos += 1 unless ok
    puts "#{ok ? '✅' : '❌'} #{nombre}"
  end
end

caso("fecha y límite válidos", "argus_debian_snapshot: \"20261115T000000Z\"\nargus_lab_llamada_vm_limite_s: 30\n") do |f, l, e, a, ap|
  f == "20261115T000000Z" && l == 30 && e.empty? && a.empty? && ap.size == 2
end
caso("fecha ausente -> error de fabricante", "argus_lab_llamada_vm_limite_s: 30\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("falta") && e[0].include?("ERROR DE FABRICANTE")
end
caso("fecha mal formada", "argus_debian_snapshot: \"2026-11-15\"\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("mal formado")
end
caso("fecha sin comillas (YAML la lee como número o texto) se trata igual",
     "argus_debian_snapshot: 20261115\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("mal formado")
end
caso("fecha imposible (30 de febrero)", "argus_debian_snapshot: \"20260230T000000Z\"\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("no es una fecha real")
end
caso("fecha anterior a la caja", "argus_debian_snapshot: \"20240101T000000Z\"\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("fuera de límites")
end
caso("fecha futura", "argus_debian_snapshot: \"20261118T000000Z\"\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("fuera de límites")
end
caso("límite ausente -> 60 con aviso", "argus_debian_snapshot: \"20261115T000000Z\"\n") do |f, l, e, a, ap|
  f && l == 60 && e.empty? && a.size == 1 && a[0].include?("falta") && ap.any? { |x| x.include?("defecto del código") }
end
caso("límite fuera de rango -> 60 con aviso", "argus_debian_snapshot: \"20261115T000000Z\"\nargus_lab_llamada_vm_limite_s: 5\n") do |_f, l, e, a, _ap|
  l == 60 && e.empty? && a.size == 1 && a[0].include?("mal")
end
caso("límite de tipo erróneo -> 60 con aviso", "argus_debian_snapshot: \"20261115T000000Z\"\nargus_lab_llamada_vm_limite_s: \"30\"\n") do |_f, l, _e, a, _ap|
  l == 60 && a.size == 1
end
caso("fichero que no es un mapa", "- uno\n- dos\n") do |f, _l, e, _a, _ap|
  f.nil? && e.size == 1 && e[0].include?("falta")
end

puts "#{$casos - $fallos}/#{$casos} casos"
exit($fallos.zero? ? 0 : 1)
