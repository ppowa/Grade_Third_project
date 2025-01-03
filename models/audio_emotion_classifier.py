import os
import random
import librosa
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoConfig, Wav2Vec2FeatureExtractor, HubertPreTrainedModel, HubertModel

project_root = os.path.dirname(os.path.abspath(__file__)) 
os.chdir(project_root)  

model_name_or_path = "xmj2002/hubert-base-ch-speech-emotion-recognition"
duration = 6
sample_rate = 16000

config = AutoConfig.from_pretrained(model_name_or_path)

def id2class(id):
    if id == 0:
        return "angry"
    elif id == 1:
        return "fear"
    elif id == 2:
        return "happy"
    elif id == 3:
        return "neutral"
    elif id == 4:
        return "sad"
    else:
        return "surprise"

def predict(path, processor, model, start_time=None, end_time=None):
    """
    Emotion analysis for an audio segment
    
    Args:
    - path: File path to the audio.
    - processor: Processor for extracting features.
    - model: Pre-trained emotion analysis model.
    - start_time: Start time (in seconds) for the audio segment.
    - end_time: End time (in seconds) for the audio segment.
    
    Returns:
    - Emotion: The predicted emotion label.
    - Score: The prediction score for the emotion.
    """
    
    speech, sr = librosa.load(path=path, sr=sample_rate, offset=start_time, duration=(end_time-start_time))
    speech = processor(speech, padding="max_length", truncation=True, max_length=duration * sr,
                       return_tensors="pt", sampling_rate=sr).input_values
    with torch.no_grad():
        logit = model(speech)
    score = F.softmax(logit, dim=1).detach().cpu().numpy()[0]
    id = torch.argmax(logit).cpu().numpy()

    emotion = id2class(id)
    emotion_score = score[id]
    emotion_scores = {id2class(i): score[i] for i in range(len(score))}

    return emotion, emotion_score ,emotion_scores


class HubertClassificationHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.classifier_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_class)

    def forward(self, x):
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)
        return x

class HubertForSpeechClassification(HubertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.hubert = HubertModel(config)
        self.classifier = HubertClassificationHead(config)
        self.init_weights()

    def forward(self, x):
        outputs = self.hubert(x)
        hidden_states = outputs[0]
        x = torch.mean(hidden_states, dim=1)
        x = self.classifier(x)
        return x

processor = Wav2Vec2FeatureExtractor.from_pretrained(model_name_or_path)
model = HubertForSpeechClassification.from_pretrained(model_name_or_path, config=config)
model.eval()

