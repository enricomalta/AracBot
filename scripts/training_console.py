"""Interactive terminal for daily local training.

Run from the repository root:
    python scripts/training_console.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.training_service import TrainingService


def ask_days() -> int:
    raw = input("Janela em dias [30]: ").strip() or "30"
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError("Informe um número inteiro de dias.") from exc


def print_training(result: dict) -> None:
    print("\nTreino concluído")
    print(f"  Versão: {result['version']}")
    print(f"  Dados: {result['total_rows']} velas | {result['data_start']} até {result['data_end']}")
    for pattern, metric in result["metrics"].items():
        if metric["trained"]:
            print(f"  {pattern}: {metric['model']} | accuracy {metric['accuracy']:.2%} | {metric['samples']} amostras")
        else:
            print(f"  {pattern}: não treinado ({metric['reason']})")
    print(f"  Backup anterior: {result.get('backup_path') or 'nenhum (primeira versão)'}")
    print("  Backups locais mantidos: 3 versões anteriores.")
    if result.get("metadata_error"):
        print(f"  AVISO: modelo salvo, mas metadados não foram gravados no Supabase: {result['metadata_error']}")


def print_recent(service: TrainingService) -> None:
    runs = service.recent_runs()
    if not runs:
        print("\nNenhum treino registrado no Supabase.")
        return
    print("\nÚltimos treinos")
    for run in runs:
        metrics = run.get("metrics") or {}
        reversal = metrics.get("reversal", {}).get("accuracy")
        continuation = metrics.get("continuation", {}).get("accuracy")
        accuracy = ", ".join(filter(None, [f"rev {reversal:.2%}" if reversal is not None else "", f"cont {continuation:.2%}" if continuation is not None else ""]))
        print(f"  {run['created_at']:%Y-%m-%d %H:%M} | {run['version']} | {run['status']} | {run['total_rows']} velas | {accuracy or 'sem métricas'}")


def main() -> None:
    service = TrainingService()
    latest_version: str | None = None
    while True:
        print("\n=== AracBot · Treinamento Local ===")
        print("1. Treinar modelo")
        print("2. Ver últimos treinos")
        print("3. Fazer deploy do último modelo treinado")
        print("0. Sair")
        choice = input("Opção: ").strip()
        try:
            if choice == "1":
                result = service.train(ask_days())
                latest_version = result["version"]
                print_training(result)
                if input("Fazer deploy na Vercel agora? [s/N]: ").strip().lower() == "s":
                    url = service.deploy(latest_version)
                    print(f"Deploy concluído: {url or 'consulte o painel Vercel'}")
            elif choice == "2":
                print_recent(service)
            elif choice == "3":
                if not latest_version:
                    raise ValueError("Treine um modelo nesta sessão antes de fazer deploy.")
                if input("Confirmar deploy do modelo atual para produção? [s/N]: ").strip().lower() == "s":
                    url = service.deploy(latest_version)
                    print(f"Deploy concluído: {url or 'consulte o painel Vercel'}")
            elif choice == "0":
                return
            else:
                print("Opção inválida.")
        except Exception as exc:
            print(f"\nErro: {exc}")


if __name__ == "__main__":
    main()
