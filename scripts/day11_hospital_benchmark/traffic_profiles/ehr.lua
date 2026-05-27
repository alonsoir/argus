-- EHR query template: small, JSON, realistic
request = function()
    local ids = {"LAB-2025-12345", "RX-98765", "ADM-55555"}
    local id = ids[math.random(#ids)]
    local body = string.format('{"query":"get_patient","id":"%s"}', id)
    return wrk.format("POST", "/ehr", {
        ["Content-Type"] = "application/json",
        ["User-Agent"] = "MLDefender-Hospital"
    }, body)
end