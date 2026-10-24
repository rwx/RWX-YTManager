"""CLI do RWX YTManager.

Comandos:
  info <url>        Metadados do video
  subs <url>        Lista idiomas de legenda
  transcript <url>  Extrai transcricao (legenda ou Whisper)
  playlist <url>    Lista videos de playlist/canal
"""

import argparse
import json
import os
import sys

from . import __version__
from . import metadata as md
from . import output as out
from . import playlist as pl
from . import subtitles as subs
from . import transcribe as tr


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_info(args):
    if args.full:
        data = md.fetch_full_metadata(args.url, ytdlp_path=args.ytdlp)
    else:
        data = md.fetch_oembed(args.url)
    if args.json:
        _print(data)
    else:
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                print("%-16s %s" % (k + ":", json.dumps(v, ensure_ascii=False)))
            else:
                print("%-16s %s" % (k + ":", v))
    return 0


def cmd_subs(args):
    langs = subs.list_subtitles(args.url, ytdlp_path=args.ytdlp)
    _print(langs)
    return 0


def cmd_playlist(args):
    entries = pl.list_entries(args.url, ytdlp_path=args.ytdlp,
                              limit=args.limit)
    if args.json:
        _print(entries)
    else:
        print("%d videos encontrados" % len(entries))
        for e in entries:
            dur = e.get("duration")
            dur = ("%dm%02ds" % divmod(int(dur), 60)) if dur else ""
            print("  %-12s %s %s" % (e.get("id"), dur, e.get("title")))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        out.write_json(entries, os.path.join(args.out, "playlist.json"))
        print("Salvo em %s/playlist.json" % args.out)
    return 0


def cmd_transcript(args):
    meta = None
    try:
        meta = md.fetch_full_metadata(args.url, ytdlp_path=args.ytdlp)
    except Exception as exc:  # metadados sao opcionais para transcricao
        print("[aviso] sem metadados completos: %s" % exc, file=sys.stderr)

    text = None
    source = None
    if not args.whisper:
        try:
            got = subs.download_subtitles(
                args.url, lang=args.lang, auto_fallback=not args.no_auto,
                ytdlp_path=args.ytdlp)
            text = subs.vtt_to_text(got["path"], dedup=True)
            source = "legenda automatica" if got["auto"] else "legenda manual"
        except Exception as exc:
            if not args.whisper_fallback:
                raise
            print("[aviso] legenda indisponivel (%s); usando Whisper..." % exc,
                  file=sys.stderr)

    if text is None:
        audio = tr.download_audio(args.url, ytdlp_path=args.ytdlp)
        text = tr.transcribe_audio(audio, model_size=args.whisper_model,
                                   language=args.lang)
        source = "whisper (%s)" % args.whisper_model

    result = {"metadata": meta, "transcript": text, "source": source}

    title = (meta or {}).get("title") or md.extract_video_id(args.url)
    base = os.path.join(args.out, out.slugify(title))
    os.makedirs(args.out, exist_ok=True)

    written = []
    if "txt" in args.format:
        written.append(out.write_text(text, base + ".txt"))
    if "json" in args.format:
        written.append(out.write_json(result, base + ".json"))
    if "md" in args.format:
        written.append(out.write_markdown(result, base + ".md"))

    meta_info = ""
    if meta:
        meta_info = " | %s | %s" % (meta.get("author"), meta.get("duration_string"))
    print("Fonte: %s | %d palavras%s" % (source, len(text.split()), meta_info))
    for w in written:
        print("Salvo: %s" % w)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="ytmanager",
        description="RWX YTManager - extracao de conteudo do YouTube.")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    p.add_argument("--ytdlp", default=os.environ.get("YTDLP_PATH", "yt-dlp"),
                   help="caminho do executavel yt-dlp (default: yt-dlp)")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("info", help="metadados do video")
    pi.add_argument("url")
    pi.add_argument("--full", action="store_true", help="metadados completos (yt-dlp)")
    pi.add_argument("--json", action="store_true")
    pi.set_defaults(func=cmd_info)

    ps = sub.add_parser("subs", help="lista idiomas de legenda")
    ps.add_argument("url")
    ps.set_defaults(func=cmd_subs)

    pp = sub.add_parser("playlist", help="lista videos de playlist/canal")
    pp.add_argument("url")
    pp.add_argument("--limit", type=int, default=None)
    pp.add_argument("--json", action="store_true")
    pp.add_argument("--out", default=None)
    pp.set_defaults(func=cmd_playlist)

    pt = sub.add_parser("transcript", help="extrai transcricao")
    pt.add_argument("url")
    pt.add_argument("--lang", default="pt", help="idioma (default: pt)")
    pt.add_argument("--no-auto", action="store_true",
                    help="nao usar legenda automatica (so manual)")
    pt.add_argument("--whisper", action="store_true",
                    help="forcar transcricao via Whisper")
    pt.add_argument("--whisper-fallback", action="store_true",
                    help="usar Whisper se nao houver legenda")
    pt.add_argument("--whisper-model", default="medium",
                    help="modelo Whisper (tiny/base/small/medium/large-v3)")
    pt.add_argument("--format", default="txt,md",
                    help="formatos de saida: txt,json,md (default: txt,md)")
    pt.add_argument("--out", default=".", help="diretorio de saida")
    pt.set_defaults(func=cmd_transcript)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "format", None):
        args.format = [f.strip() for f in args.format.split(",") if f.strip()]
    try:
        return args.func(args)
    except RuntimeError as exc:
        print("Erro: %s" % exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
