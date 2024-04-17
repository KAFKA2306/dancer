import random
import yaml

def select_parameters():
    # パラメータファイルの読み込み
    with open('parameters.yaml', 'r') as file:
        parameters = yaml.safe_load(file)

    # パラメータのランダムな選択
    avatar = random.choice(parameters['avatars'])
    motion = random.choice(parameters['motions'])
    music = random.choice(parameters['music'])
    background = random.choice(parameters['backgrounds'])

    return avatar, motion, music, background
