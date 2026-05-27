# paper_section_generator.py
def generate_hospital_performance_section():
    section = f"""
\\section{{Performance in Medical Environments}}
\\label{{sec:hospital-performance}}

\\subsection{{Test Methodology}}
The hospital validation suite (Day 11) consisted of three traffic profiles:

\\begin{{itemize}}
    \\item \\textbf{{EHR Traffic}}: Simulated HL7/FHIR queries ({ehr_count} requests)
    \\item \\textbf{{PACS Bursts}}: Medical imaging DICOM transfers ({pacs_size}MB bursts)
    \\item \\textbf{{Emergency Alerts}}: Critical notifications during peak load
\\end{{itemize}}

\\subsection{{Results}}
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{lccc}}
\\hline
\\textbf{{Metric}} & \\textbf{{Target}} & \\textbf{{Achieved}} & \\textbf{{Status}} \\\\
\\hline
EHR Latency (p99) & < 50ms & {ehr_latency}ms & {ehr_status} \\\\
PACS Packet Loss & 0\\% & {pacs_loss}\\% & {pacs_status} \\\\
False Positives & < 0.1\\% & {false_positives}\\% & {fp_status} \\\\
CPU Usage (peak) & < 40\\% & {cpu_peak}\\% & {cpu_status} \\\\
\\hline
\\end{{tabular}}
\\caption{{Hospital Network Performance Metrics}}
\\label{{tab:hospital-metrics}}
\\end{{table}}

\\subsection{{Clinical Readiness Assessment}}
Based on Day 11 validation, ML Defender {readiness_verdict} for deployment 
in healthcare environments requiring sub-50ms latency and zero packet loss 
for critical medical traffic.
"""
    return section