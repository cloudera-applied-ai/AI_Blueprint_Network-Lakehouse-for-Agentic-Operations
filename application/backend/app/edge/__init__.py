"""Edge data center anomaly flow.

An operator picks a headend (the NOC's data-center entity) and a scenario; the
headend's local model runs a scripted detect/contain thought-stream, stages a
suspect pcap to S3 (or local disk), and the primary-DC poller ingests it
through the shared pcap analysis pipeline.
"""
