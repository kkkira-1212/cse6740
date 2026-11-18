"""Safeguards for negative direction and validation-only LoRA training."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
import torch.nn.functional as F

SPEC = importlib.util.spec_from_file_location("train_clip_lora", Path(__file__).resolve().parents[1] / "src/models/train_clip_lora.py")
training = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(training)


class ContrastiveTests(unittest.TestCase):
    def test_full_mode_keeps_every_parameter_trainable(self):
        from transformers import CLIPConfig, CLIPModel
        tiny = CLIPModel(CLIPConfig(
            text_config={"vocab_size": 20, "hidden_size": 16, "intermediate_size": 32,
                         "num_hidden_layers": 1, "num_attention_heads": 2, "max_position_embeddings": 8,
                         "bos_token_id": 1, "eos_token_id": 2},
            vision_config={"hidden_size": 16, "intermediate_size": 32, "num_hidden_layers": 1,
                           "num_attention_heads": 2, "image_size": 8, "patch_size": 4},
            projection_dim=8,
        ))
        with patch.object(training.CLIPModel, "from_pretrained", return_value=tiny):
            model, targets = training.make_model({
                "training_mode": "full", "model_id": "unused", "model_revision": "unused"
            })
        self.assertEqual(targets, [])
        self.assertTrue(all(parameter.requires_grad for parameter in model.parameters()))

    def test_optimizer_changes_adapters_but_not_backbone(self):
        from transformers import CLIPConfig, CLIPModel
        from peft import LoraConfig, get_peft_model
        torch.manual_seed(0)
        config = CLIPConfig(
            text_config={"vocab_size": 20, "hidden_size": 16, "intermediate_size": 32,
                         "num_hidden_layers": 1, "num_attention_heads": 2, "max_position_embeddings": 8,
                         "bos_token_id": 1, "eos_token_id": 2},
            vision_config={"hidden_size": 16, "intermediate_size": 32, "num_hidden_layers": 1,
                           "num_attention_heads": 2, "image_size": 8, "patch_size": 4},
            projection_dim=8,
        )
        model = get_peft_model(CLIPModel(config), LoraConfig(r=2, lora_alpha=4, target_modules=["q_proj", "v_proj"]))
        before = {name: p.detach().clone() for name, p in model.named_parameters()}
        ids = torch.tensor([[1, 4, 2], [1, 5, 2], [1, 6, 2], [1, 7, 2]])
        masks = training.positive_masks(ids, torch.ones_like(ids), 2)
        images = training.embedding(model.get_image_features(pixel_values=torch.randn(2, 3, 8, 8)))
        texts = training.embedding(model.get_text_features(input_ids=ids, attention_mask=torch.ones_like(ids)))
        training.contrastive_loss(images, texts, masks, .07).backward()
        torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=.001).step()
        changed = [name for name, p in model.named_parameters() if not torch.equal(before[name], p)]
        self.assertTrue(any("vision_model" in n for n in changed))
        self.assertTrue(any("text_model" in n for n in changed))
        self.assertTrue(all("lora_" in n for n in changed))

    def test_unique_titles_match_two_direction_cross_entropy(self):
        images = F.normalize(torch.randn(3, 8), dim=1)
        texts = F.normalize(torch.randn(6, 8), dim=1)
        mask = torch.cat([torch.eye(3, dtype=torch.bool), torch.zeros(3, 3, dtype=torch.bool)], dim=1)
        logits = images @ texts.T / 0.07
        expected = (F.cross_entropy(logits, torch.arange(3)) + F.cross_entropy(logits[:, :3].T, torch.arange(3))) / 2
        actual = training.contrastive_loss(images, texts, (mask, mask[:, :3].T), 0.07)
        torch.testing.assert_close(actual, expected)

    def test_explicit_negative_scores_receive_downward_gradient(self):
        logits = torch.tensor([[1., 2.]], requires_grad=True)
        loss = training.multi_positive_nce(logits, torch.tensor([[True, False]]))
        loss.backward()
        self.assertLess(logits.grad[0, 0], 0)
        self.assertGreater(logits.grad[0, 1], 0)

    def test_duplicate_donor_title_is_known_positive_for_its_own_image(self):
        ids = torch.tensor([[1, 4, 2], [1, 5, 2], [1, 5, 2], [1, 6, 2]])
        forward, reverse = training.positive_masks(ids, torch.ones_like(ids), 2)
        self.assertEqual(forward.tolist(), [[True, False, False, False], [False, True, True, False]])
        self.assertEqual(reverse.tolist(), [[True, False], [False, True]])

    def test_padding_is_ignored_in_known_positive_matching(self):
        ids = torch.tensor([[1, 2, 0], [1, 2, 9]])
        mask = torch.tensor([[1, 1, 0], [1, 1, 0]])
        forward, _ = training.positive_masks(ids, mask, 1)
        self.assertEqual(forward.tolist(), [[True, True]])

    def test_missing_positive_rejected(self):
        with self.assertRaises(ValueError):
            training.multi_positive_nce(torch.ones(1, 2), torch.zeros(1, 2, dtype=torch.bool))


class DatasetTests(unittest.TestCase):
    def test_fixed_release_split_isolation_and_training_counts(self):
        rows, anchors = training.read_dataset(training.ROOT / "data/releases/abo-home-v2-20261103/pairs.csv", "abo-home-v2-20261103")
        self.assertEqual({k: len(v) for k, v in anchors.items()}, {"train": 2664, "val": 328, "test": 343})
        self.assertTrue(all(r["split"] == "train" for pair in anchors["train"] for r in pair))
        bad = [dict(r) for r in rows]
        bad[-1]["image_path"] = rows[0]["image_path"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pairs.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(bad[0]))
                writer.writeheader()
                writer.writerows(bad)
            with self.assertRaisesRegex(ValueError, "crosses splits"):
                training.read_dataset(path, "abo-home-v2-20261103")


if __name__ == "__main__":
    unittest.main()
