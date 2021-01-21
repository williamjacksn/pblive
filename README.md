# PBLive

PBLive is an open-source self-hosted live online quiz tool, similar to Kahoot and Socrative.

This repository was forked from https://yingtongli.me/git/PBLive/

## Installing and running

    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    export QUIZ_SERVER_URL="http://localhost:5000"
    python -m pblive

Navigate to http://1.2.3.4:5000/admin to begin.

## Example

Place in `data/example.yaml`, where the `data` directory is a sibling of this README:

    title: Example quiz
    questions:
    - type: landing
    - type: mcq
      prompt: This is a multiple-choice question
      answers: [A, B, C, D]
    - type: type
      prompt: This is a basic short answer question
    - type: type
      prompt: The answer to this short answer question is a percentage
      answer_form: $1%
      answer_type: number
      answer_range: [0, 100]
    - type: draw
      prompt: Draw on the diagram
      image: some_image.gif
    - type: speed
      prompt: A speed quiz is like multiple-choice, but starts a two second countdown once the first answer is submitted to each question.
      answers: [Option 1, Option 2, Option 3]
    - type: speed
      prompt: This will automatically continue until the last speed question in a row is completed.
      answers: [Option 1, Option 2, Option 3]
    - type: speed
      prompt: The answers to the speed questions are reviewed in a review stage following the final question.
      answers: [Option 1, Option 2, Option 3]
    - type: speed_review

Files like `some_image.gif` should be placed within the `img` subfolder of `data`.

## Docker

### Example

```bash
# build
docker build -t pblive .

docker run --rm -v `pwd`/example.yaml:/pblive/data/example.yaml -e "QUIZ_SERVER_URL=http://localhost:5000"  -p 5000:5000 pblive
```

## Security

There is none. Watch this space.

## Licence

    Copyright © 2017  RunasSudo (Yingtong Li)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
