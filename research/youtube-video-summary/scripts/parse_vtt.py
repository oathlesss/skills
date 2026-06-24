#!/usr/bin/env python3
"""Parse a YouTube auto-generated VTT file into clean, deduplicated, chunked text.

Usage: python3 parse_vtt.py <vtt_path> [--chunks N] [--out-prefix /tmp/vid]
"""
import re, sys, os

def parse_vtt(vtt_path, num_chunks=5, out_prefix=None):
    if out_prefix is None:
        out_prefix = os.path.splitext(vtt_path)[0]

    with open(vtt_path) as f:
        content = f.read()

    lines = content.split('\n')
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line == 'WEBVTT' or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        if '-->' in line or line.startswith('align:'):
            continue
        line = re.sub(r'<[^>]+>', '', line).strip()
        if line and not re.match(r'^\d{2}:', line):
            text_lines.append(line)

    # Deduplicate consecutive lines (auto-caption quirk)
    deduped = []
    for line in text_lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    text = ' '.join(deduped)
    clean_path = f"{out_prefix}_clean.txt"
    with open(clean_path, 'w') as f:
        f.write(text)

    # Split into sentence-based chunks (read_file truncates single-line files)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunk_size = len(sentences) // num_chunks

    for i in range(num_chunks):
        start = i * chunk_size
        end = start + chunk_size if i < num_chunks - 1 else len(sentences)
        chunk = ' '.join(sentences[start:end])
        chunk_path = f"{out_prefix}_chunk{i}.txt"
        with open(chunk_path, 'w') as f:
            f.write(chunk)

    return len(deduped), len(text)

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('vtt_path')
    p.add_argument('--chunks', type=int, default=5)
    p.add_argument('--out-prefix', default=None)
    args = p.parse_args()
    lines, chars = parse_vtt(args.vtt_path, args.chunks, args.out_prefix)
    print(f"Parsed {lines} lines, {chars} chars -> {args.chunks} chunks at {args.out_prefix or os.path.splitext(args.vtt_path)[0]}_chunk*.txt")
