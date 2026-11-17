# frozen_string_literal: true
# [DEBIAN-FECHA-D329] aRGus NDR -- valores comunes a todas las lentes del laboratorio
# (ansible/inventory/group_vars/all.yml). Una sola validación para el Vagrantfile y para make kernel-homogeneo.
#
#   argus_debian_snapshot          AAAAMMDDTHHMMSSZ (UTC), fecha real, de 20240905T000000Z al momento actual.
#                                  Sin defecto: falta o mal -> error (de fabricante); quien lo use para.
#   argus_lab_llamada_vm_limite_s  entero [10, 600]. Falta o mal -> 60, con aviso.
#
# Ningún valor se lee en silencio: cargar devuelve, además de errores y avisos, una línea por campo con el valor
# aplicado y de dónde sale.
#
# Uso (anfitrión): ruby lab_comun.rb fecha <all.yml>   -> imprime la fecha; errores y avisos a stderr; rc 1 si error
#                  ruby lab_comun.rb limite <all.yml>  -> imprime el límite; la línea de origen a stderr
require "yaml"

module ArgusLabComun
  FECHA_RE = /\A\d{8}T\d{6}Z\z/
  FECHA_MIN = "20240905T000000Z"
  LIMITE_DEFECTO = 60
  LIMITE_MIN = 10
  LIMITE_MAX = 600
  FABRICANTE = "ERROR DE FABRICANTE: avisar a aRGus (el laboratorio debió verlo antes); no es un fallo del despliegue"

  # -> [fecha_o_nil, limite, errores, avisos, aplicados]
  def self.cargar(ruta, ahora = Time.now.utc)
    errores = []
    avisos = []
    aplicados = []
    datos = begin
      YAML.safe_load(File.read(ruta)) || {}
    rescue StandardError => e
      return [nil, LIMITE_DEFECTO, ["#{ruta}: no se puede leer (#{e.class}: #{e.message}). #{FABRICANTE}"], [], []]
    end
    datos = {} unless datos.is_a?(Hash)

    fecha = nil
    f = datos["argus_debian_snapshot"]
    formato = "formato AAAAMMDDTHHMMSSZ (UTC), de #{FECHA_MIN} al momento actual"
    if f.nil?
      errores << "argus_debian_snapshot: falta en #{ruta} (#{formato}). #{FABRICANTE}"
    elsif !(f.is_a?(String) && FECHA_RE.match?(f))
      errores << "argus_debian_snapshot: #{f.inspect} mal formado en #{ruta} (#{formato}). #{FABRICANTE}"
    else
      t = begin
        Time.utc(f[0, 4].to_i, f[4, 2].to_i, f[6, 2].to_i, f[9, 2].to_i, f[11, 2].to_i, f[13, 2].to_i)
      rescue ArgumentError
        nil
      end
      if t.nil? || t.strftime("%Y%m%dT%H%M%SZ") != f
        errores << "argus_debian_snapshot: #{f} no es una fecha real en #{ruta} (#{formato}). #{FABRICANTE}"
      elsif f < FECHA_MIN || t > ahora
        errores << "argus_debian_snapshot: #{f} fuera de límites en #{ruta} (#{formato}). #{FABRICANTE}"
      else
        fecha = f
        aplicados << "argus_debian_snapshot=#{f} (de #{ruta})"
      end
    end

    limite = LIMITE_DEFECTO
    l = datos["argus_lab_llamada_vm_limite_s"]
    rango = "entero [#{LIMITE_MIN}, #{LIMITE_MAX}]"
    if l.nil?
      avisos << "argus_lab_llamada_vm_limite_s: falta en #{ruta} (#{rango}); se aplica #{LIMITE_DEFECTO}"
      aplicados << "argus_lab_llamada_vm_limite_s=#{LIMITE_DEFECTO} (defecto del código: falta en #{ruta})"
    elsif !l.is_a?(Integer) || l < LIMITE_MIN || l > LIMITE_MAX
      avisos << "argus_lab_llamada_vm_limite_s: #{l.inspect} mal en #{ruta} (#{rango}); se aplica #{LIMITE_DEFECTO}"
      aplicados << "argus_lab_llamada_vm_limite_s=#{LIMITE_DEFECTO} (defecto del código: #{l.inspect} mal formado)"
    else
      limite = l
      aplicados << "argus_lab_llamada_vm_limite_s=#{l} (de #{ruta})"
    end

    [fecha, limite, errores, avisos, aplicados]
  end
end

if $PROGRAM_NAME == __FILE__
  campo, ruta = ARGV
  unless %w[fecha limite].include?(campo) && ruta
    warn "uso: ruby #{File.basename(__FILE__)} fecha|limite <all.yml>"
    exit 2
  end
  fecha, limite, errores, avisos, aplicados = ArgusLabComun.cargar(ruta)
  avisos.each { |a| warn "[DEBIAN-FECHA-D329] ⚠️  AVISO #{a}" }
  if campo == "fecha"
    unless errores.empty?
      errores.each { |e| warn "[DEBIAN-FECHA-D329] ❌ #{e}" }
      exit 1
    end
    aplicados.grep(/\Aargus_debian_snapshot=/).each { |a| warn "[DEBIAN-FECHA-D329] aplicado #{a}" }
    puts fecha
  else
    aplicados.grep(/\Aargus_lab_llamada_vm_limite_s=/).each { |a| warn "[DEBIAN-FECHA-D329] aplicado #{a}" }
    puts limite
  end
end
