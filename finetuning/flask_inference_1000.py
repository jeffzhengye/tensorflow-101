import tensorflow as tf
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
slim = tf.contrib.slim
from PIL import Image
from nets.inception_v3 import *
import numpy as np
import os
import time
import uuid
"""
Load a tensorflow model and make it available as a REST service
"""
app = Flask(__name__)
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['jpg', 'png', 'jpeg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class myTfModel(object):
    def __init__(self, checkpoint_file):
        self.checkpoint_file = checkpoint_file
        self.output = {}
        self.load_model()

    def load_model(self):
        sess = tf.Session()
        input_tensor = tf.placeholder(tf.float32, [None, 299, 299, 3])
        arg_scope = inception_v3_arg_scope()
        with slim.arg_scope(arg_scope):
            logits, end_points = inception_v3(
                input_tensor, is_training=False, num_classes=1001)
            saver = tf.train.Saver()
        # params_file = tf.train.latest_checkpoint(self.model_dir)
        saver.restore(sess, self.checkpoint_file)
        self.output['sess'] = sess
        self.output['input_tensor'] = input_tensor
        self.output['logits'] = logits
        self.output['end_points'] = end_points
        # return sess, input_tensor, logits, end_points

    def execute(self, data, **kwargs):
        sess = self.output['sess']
        input_tensor = self.output['input_tensor']
        logits = self.output['logits']
        end_points = self.output['end_points']
        # ims = []
        # for i in range(kwargs['batch_size']):
        im = Image.open(data).resize((299, 299))
        im = np.array(im) / 255.0
        im = im.reshape(-1, 299, 299, 3)
        # ims.append(im)
        # ims = np.array(ims)
        # print ims.shape
        start = time.time()
        predict_values, logit_values = sess.run(
            [end_points['Predictions'], logits], feed_dict={input_tensor: im})
        return predict_values
        # print 'the porn score with the {0} is {1} '.format(

    # data, predict_values[1][1])
    # print 'a image take time {0}'.format(time.time() - start)


mymodel = myTfModel('./pretrain_model/inception_v3.ckpt')


def get_label(sysnet_file, metadata_file):
    index_sysnet = []
    with open(sysnet_file, 'r') as fread:
        for line in fread.readlines():
            line = line.strip('\n')
            index_sysnet.append(line)
    sys_label = {}
    with open(metadata_file, 'r') as fread:
        for line in fread.readlines():
            index = line.strip('\n').split('\t')[0]
            val = line.strip('\n').split('\t')[1]
            sys_label[index] = val

    index_label = [sys_label[i] for i in index_sysnet]
    index_label.append("i don't know")
    return index_label


# @app.route('/model', methods=['GET', 'POST'])
# def apply_model():
#     image = request.args.get('image')
#     predict_values = mymodel.execute(image, batch_size=1)
#     predicted_class_top5 = reversed(np.argsort(predict_values[0])[-5:])
#     index_label = get_label('./sysnet.txt', 'imagenet_metadata.txt')
#     labels = [index_label[i] for i in predicted_class_top5]
#     return jsonify(result=','.join(labels))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # add the filename to uuid
            file_type = filename.split('.')[1]
            file_name_ori = filename.split('.')[0]
            filename = str(uuid.uuid4()) + '.' + file_type

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('result', filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>    
    '''


from flask import send_from_directory


@app.route('/uploads/<filename>', methods=['GET', 'POST'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/result/<filename>', methods=['GET'])
def result(filename):
    image = os.path.join(UPLOAD_FOLDER, filename)
    predict_values = mymodel.execute(image, batch_size=1)
    predicted_class_top5 = reversed(np.argsort(predict_values[0])[-5:])
    index_label = get_label('./sysnet.txt', 'imagenet_metadata.txt')
    labels = [index_label[i - 1] for i in predicted_class_top5]

    result = 'inference result: ' + '\n'.join(labels)
    return "<!doctype html><title>Upload new File</title><h1>Result</h1><img height ='400', width='400' src='/uploads/{0}'></img></br>{1}".format(
        filename, result)


if __name__ == '__main__':
    app.run(debug=True)