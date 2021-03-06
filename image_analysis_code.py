#image analysis eind opdracht code 
import numpy as np
import pandas as pd
import argparse
import ast
from keras.callbacks import EarlyStopping
from keras.callbacks import TensorBoard
from keras.layers import Dense, Activation, Flatten, Dropout
from keras.layers import MaxPooling2D
from keras.layers.convolutional import Conv2D
from keras.models import Sequential
from keras.utils import np_utils
from keras.utils import multi_gpu_model
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

def main():
    labels, disease_X_images = import_data()
    fitted_labels = encode_labels(labels)
    arguments = get_user_arguments()
    """
    default arguments are:batch_size=100, channels=1, img_collums=256, img_rows=256, kernel_size=(2, 2),
    nb_classes=15, nb_epochs=20, nb_filters=32, nb_gpus=8, test_data_size=0.2, use_GPU=False.
    """
    
    disease_X_train_array, disease_X_test_array, disease_y_train_array, disease_y_test_array = split_data(disease_X_images, fitted_labels, float(arguments.test_data_size))
    disease_X_train_reshaped_array, disease_X_test_reshaped_array = reshape_data(disease_X_train_array, disease_X_test_array, int(arguments.img_rows), int(arguments.img_collums), int(arguments.channels))
    disease_X_train_normalized_array, disease_X_test_normalized_array = normalize_data(disease_X_train_reshaped_array, disease_X_test_reshaped_array)
    disease_y_train_matrix, disease_y_test_matrix = transform_categorical_data(disease_y_train_array, disease_y_test_array, int(arguments.nb_classes))

    input_shape = get_input_shape(int(arguments.img_rows), int(arguments.img_collums), int(arguments.channels))
    model = create_model(disease_X_train_normalized_array, disease_y_train_matrix, arguments.kernel_size, int(arguments.nb_filters), int(arguments.channels),
                         int(arguments.nb_epochs), int(arguments.batch_size), int(arguments.nb_gpus), arguments.use_GPU, input_shape, int(arguments.nb_classes))

    disease_y_prediction = test_model(model, disease_X_test_normalized_array, disease_y_test_matrix) 
    precision, recall, f1 = calculate_results(disease_y_test_matrix, disease_y_prediction)
    print_results(precision, recall, f1)
    
def get_user_arguments():
    """
    Initialize a ArgumentParset object and add all the user definable arguments.
    input:
         image_amount: int, the total amount of images 
    output:
         arguments: ArgumentParset object containg the user defined variables or the default values. 
    """
    parser = argparse.ArgumentParser(description="analyze lung images, the input data is created using another script",
                                     epilog="Example query:\npython3 image_analysis_code.py -b 100 -a 15 -e 20 -s 0.2 -r 256 -c 256 -d 1 -f 32 -k 2 2")
    parser.add_argument("-v", "--version", help="Display current version of the program and exit", action="version", version="Version 1.0")
    parser.add_argument("-b","--batch_size", help="Number of samples used per iteration to train the model[default=100]", type=int, default=100)
    parser.add_argument("-a","--nb_classes", help="Total number of classes the test data has[default=15]", type=int, default=15)
    parser.add_argument("-e","--nb_epochs", help="the number of complete passes through the dataset[default=20]", type=int, default=20)
    parser.add_argument("-s", "--test_data_size", help="what percentage of train data should be used as test data?[default=0.2]", type=is_test_data_size_valid, default=0.2)
    parser.add_argument("-gpu","--use_GPU", help="Enable the use of a GPU to accelerate the process(if a NVIDIA gpu is installed on the device)", action="store_true", default=False)
    parser.add_argument("-g","--nb_gpus", help="the number of gpus used in this run(if -gpu/--use_gpu is selected)[default=8]", type=int, default=8)
    parser.add_argument("-r","--img_rows", help="each image will be, unless already, trimmed to this number of rows[default=256]", type=int, default=256)
    parser.add_argument("-c","--img_collums", help="each image will be, unless already, trimmed to this number of collums[default=256]", type=int, default=256)
    parser.add_argument("-d","--channels", help="Specify if the image is grayscale (1) or RGB (3)[default=1]", type=int, choices=[1,3], default=1)
    parser.add_argument("-f","--nb_filters", help="The number of kernels used to convolve the images.\nThe amount of filters increases twice exponentionally. For example: 32, 64, 128.[default=32]", type=int, default=32)
    parser.add_argument("-k","--kernel_size", help="Specify the height and width of the convolutional window[default=(2 2)], enter as: 2 2", type=ast.literal_eval, nargs=2, default=(2, 2))
    arguments = parser.parse_args()
    return arguments

def is_test_data_size_valid(test_data_size):
    if float(test_data_size) > 0.0 and float(test_data_size) < 1.0:
        return test_data_size
    else:
        message="The test_data_size is invalid. It should be between 0.0 and 1.0"
        raise argparse.ArgumentTypeError(message)

def import_data():
    """
    import the data.
    Disease_X_images contains the images for disease X.
    Labels contains per image a label noting what the disease is.
    Returns a numpy array of images containing the disease and the associated labels. 
    """
    try:
        disease_X_images = np.load("data/X_sample.npy")
        labels = pd.read_csv("data/sample_labels.csv")
    except FileNotFoundError:
        print("the file\"X_sample.npy\" or \"sample_labels.csv\", was not found.\nMake sure that the script is located in the following directory:\n script\n-data\n--X_sample.npy\n--sample_labels.csv")
    except IOError:
        print("Something went wrong while reading in the files.\nAre the files corrupted? Are the files in the right format(.csv and .npy)?\nFix the issue before continueing")
    except:
        print("Something went wrong while reading in the files.\nCheck if the files \"sample_lables.csv\" and the \"X_sample.npy\" files are available")
    return labels, disease_X_images

def encode_labels(labels):
    """
    Transform the labels(text) into numbers. For example: ["aap", "aap", "vis", "banaan"] = [0, 0, 1, 2]
    input:
         labels: panda series
    output:
        fitted labels, see example above. 
    """
    fitted_labels = labels.Finding_Labels
    # fitted_labels = np.array(pd.get_dummies(fitted_labels))
    label_encoder = LabelEncoder()
    fitted_labels = label_encoder.fit_transform(fitted_labels)
    fitted_labels = fitted_labels.reshape(-1, 1)
    return fitted_labels

def split_data(disease_X_images, fitted_labels, test_data_size=0.2):
    """
    Split data into test and training datasets.
    input:
        disease_X_images: NumPy array of arrays
        fitted_labels   : Pandas series, which are the labels for input array X
        test_data_size  : size of test/train split. Value from 0 to 1 (default=0.2)
    output:
        Four arrays: disease_X_train_array, disease_X_test_array, disease_y_train_array, disease_y_test_array
    """
    print("Splitting data into test/ train datasets")
    disease_X_train_array, disease_X_test_array, disease_y_train_array, disease_y_test_array = train_test_split(disease_X_images, fitted_labels, test_size=test_data_size)
    return disease_X_train_array, disease_X_test_array, disease_y_train_array, disease_y_test_array

def reshape_data(disease_X_train_array, disease_X_test_array, img_rows, img_cols, channels):
    """
    Reshape the data into the format for CNN.
    Input:
         disease_X_train_array: NumPy X_disease train array dataset
         disease_X_test_array : NumPy X_disease test array dataset
         img_rows             : int denoting the amount of favored rows
         img_cols             : int denoting the amount of favored collums
         channels             : Specify if the image is grayscale (1) or RGB (3)
    output:
          disease_X_train_reshaped_array
          disease_X_test_reshaped_array
    """
    print("Reshaping Data")
    disease_X_train_reshaped_array = disease_X_train_array.reshape(disease_X_train_array.shape[0], img_rows, img_cols, channels)
    disease_X_test_reshaped_array = disease_X_test_array.reshape(disease_X_test_array.shape[0], img_rows, img_cols, channels)

    print("X_train Shape: ", disease_X_train_reshaped_array.shape)
    print("X_test Shape: ", disease_X_test_reshaped_array.shape)
    return disease_X_train_reshaped_array, disease_X_test_reshaped_array

    
def get_input_shape(img_rows, img_cols, channels):
    """
    get the input shape.
    input:
         img_rows: the amount of rows the images have
         img_cols: the amount of collums the images have
         channels: specify if the image is grayscale (1) or RGB (3)
    output:
         input_shape: a tuple denoting the input shape of all images 
    """
    input_shape = (img_rows, img_cols, channels)
    return input_shape

def normalize_data(disease_X_train_reshaped_array, disease_X_test_reshaped_array):
    """
    Normalize the data.
    input:
         disease_X_train_reshaped_array: NumPy X_disease train array dataset reshaped
         disease_X_test_reshaped_array : NumPy X_disease test array dataset reshaped
    output:
         disease_X_train_normalized_array: NumPy X_disease train array dataset reshaped and normalized
         disease_X_test_normalized_array : NumPy X_disease test array dataset reshaped and normalized
    """
    print("Normalizing Data")
    disease_X_train_normalized_array = disease_X_train_reshaped_array.astype('float32')
    disease_X_test_normalized_array = disease_X_test_reshaped_array.astype('float32')

    disease_X_train_normalized_array /= 255
    disease_X_test_normalized_array /= 255

    return disease_X_train_normalized_array, disease_X_test_normalized_array

def transform_categorical_data(disease_y_train_array, disease_y_test_array, nb_classes):
    """
    transform the Y_disease NumPy array dataset into a one-hot-encoding matrix.
    for example: [0,1,0,2] = [[1,0,0][0,1,0][1,0,0][0,0,1]]
    input:
         disease_y_train_array: NumPy y_disease train array dataset
         disease_y_test_array : NumPy y_test train array dataset.
         nb_classes           : total number of classes
    output:
         disease_y_train_matrix: a matrix containing categorical data of y_disease
         disease_y_test_matrix : a matrix containing categorical data of y_disease
    """
    disease_y_train_matrix = np_utils.to_categorical(disease_y_train_array, nb_classes)
    disease_y_test_matrix = np_utils.to_categorical(disease_y_test_array, nb_classes)
    
    print("y_train Shape: ", disease_y_train_matrix.shape)
    print("y_test Shape: ", disease_y_test_matrix.shape)
    return disease_y_train_matrix, disease_y_test_matrix

def create_model(disease_X_train_normalized_array, disease_y_train_matrix, kernel_size, nb_filters, channels, nb_epoch,
                 batch_size, nb_gpus, use_GPU, input_shape, nb_classes):
    """
    create the model existing of 3 layers. Firstly create a model that convolves the images(3 times),
    then apply flatten and dropout layers to prevent overfitting,
    compile the model and lastly train the model using the early predefined layers. 
    input:
        disease_X_train_normalized_array: Array of NumPy arrays
        disease_y_train_matrix: Array of labels
        kernel_size: Initial size of kernel
        nb_filters: Initial number of filters
        channels: Specify if the image is grayscale (1) or RGB (3)
        nb_epoch: Number of epochs
        batch_size: Batch size for the model
        nb_gpus:  number of GPUs or list of GPU IDs on which to create model replicas
        use_GPU: boolean. True means GPU should be used, False means GPU should/cannot be used.
        input_shape: tuple with the input shape of the images
    output:
         model: a fitted CNN model 
    """
    model = get_model()
    model = add_convolving_layers_to_model(model, input_shape, nb_filters, kernel_size)
    model = add_convolving_layers_to_model(model, input_shape, nb_filters=nb_filters*2, kernel_size=[i * 2 for i in kernel_size])#default should change to:(4, 4))
    model = add_convolving_layers_to_model(model, input_shape, nb_filters=nb_filters*4, kernel_size=[i * 4 for i in kernel_size])#default should change to:(8, 8))
    model = flatten_and_add_dropout_layers_to_model(model, nb_classes)
    model = compile_model(model, nb_gpus, use_GPU)
    print(model.summary())
    model = train_model(model, disease_X_train_normalized_array, disease_y_train_matrix, nb_epoch, batch_size)
    return model

def get_model():
    """
    define the model.
    input:
         -
    output:
         model: a initialized Sequential model. 
    """
    model = Sequential()
    return model

def add_convolving_layers_to_model(model, input_shape, nb_filters, kernel_size):
    """
    Add to the model convolving and ReLU layers.AttributeError: 'Sequential' object has no attribute '_get_distribution_strategy'

    First set of three layers
    input:
         model      : a Sequential model
         nb_filters : total amount of filters. 
         kernel_size: initial size of the kernel
         input_shape: the input shape the images have
    output:
         model: A sequential CNN model.
    """
    
    model.add(Conv2D(nb_filters, (kernel_size[0], kernel_size[1]),
                     padding='valid',
                     strides=1,
                     input_shape=input_shape))
    model.add(Activation('relu'))

    model.add(Conv2D(nb_filters, (kernel_size[0], kernel_size[1])))
    model.add(Activation('relu'))

    model.add(Conv2D(nb_filters, (kernel_size[0], kernel_size[1])))
    model.add(Activation('relu'))

    model.add(MaxPooling2D(pool_size=(2, 2)))
    return model

def flatten_and_add_dropout_layers_to_model(model, nb_classes):
    """
    Flatten and add dropout layers to the model.
    input:
         model: a sequential CNN model
    output:
         model: a sequential CNN model 
    """
    model.add(Flatten())
    print("Model flattened out to: ", model.output_shape)

    model.add(Dense(4096))
    model.add(Activation('relu'))
    model.add(Dropout(0.2))

    model.add(Dense(4096))
    model.add(Activation("relu"))
    model.add(Dropout(0.2))

    model.add(Dense(nb_classes))
    model.add(Activation('softmax'))
    return model

def compile_model(model, nb_gpus, use_GPU):
    """
    compile the model to use multiple GPU's.
    input:
         model  : a sequential CNN model
         nb_gpus: number of GPUs or list of GPU IDs on which to create model replicas
         use_GPU: boolean. True means GPU should be used, False means GPU should/cannot be used.
    output:    
         model: a sequential CNN model
    """
    if use_GPU == True:
        model = multi_gpu_model(model, gpus=nb_gpus)
    model.compile(loss='categorical_crossentropy',
                  optimizer='adam',
                  metrics=['accuracy'])

    return model

def train_model(model, disease_X_train_normalized_array, disease_y_train_matrix, nb_epoch, batch_size):
    """
    The model is defined using above defined layers. Now it is time to train(update the weights of the filters) the model.
    input:
         model                           : a sequential CNN model
         disease_X_train_normalized_array: NumPy array of normalized X_disease train dataset
         disease_y_train_matrix          : matrix of categorical y_disease data
         nb_epoch                        : Number of epochs
         batch_size                      : batch size for the model 
    output:
         model: a trained sequential CNN model
    """
    stop = EarlyStopping(monitor='acc',
                         min_delta=0.001,
                         patience=2,
                         verbose=0,
                         mode='auto')

    tensor_board = TensorBoard(log_dir='./Graph', histogram_freq=0, write_graph=True, write_images=True)

    model.fit(disease_X_train_normalized_array, disease_y_train_matrix, batch_size=batch_size, epochs=nb_epoch,
              verbose=1,
              validation_split=0.2,
              class_weight='auto',
              callbacks=[stop, tensor_board]
              )
    return model

def test_model(model, disease_X_test_normalized_array, disease_y_test_matrix):
    """
    Test the model.
    input:
         model                          : the fitted CNN model
         disease_X_test_normalized_array: NumPy array with the X_disease test data
         disease_y_test_matrix          : a matrix with the y_disease test data
    output:
         disease_y_prediction: NumPy array with the test/prediction of the model
    """

    print("testing")
    disease_y_prediction = model.predict(disease_X_test_normalized_array)

    disease_y_test_matrix = np.argmax(disease_y_test_matrix, axis=1)
    disease_y_prediction = np.argmax(disease_y_prediction, axis=1)
    return disease_y_prediction


def calculate_results(disease_y_test_matrix, disease_y_prediction):
    """
    calculate the precision, recall and f1 using the test data, aka: disease_y data.
    input:
         disease_y_test_matrix: a matrix with the test data
         disease_y_prediction : NumPy array with the test/prediction of the model
    output:
         precision: the precision of the model
         recall   : the recall of the model
         f1       : the f1 score of the model
    """
    precision = precision_score(disease_y_test_matrix, disease_y_prediction, average='weighted')
    recall = recall_score(disease_y_test_matrix, disease_y_prediction, average='weighted')
    f1 = f1_score(disease_y_test_matrix, disease_y_prediction, average="weighted")
    return precision, recall, f1

def print_results(precision, recall, f1):
    """
    print the results of the model.
    input:
         precision: the precision of the model
         recall   : the recall of the model
         f1       : the f1 score of the model
    """
    print("Precision: ", precision)
    print("Recall: ", recall)
    print("F1: ", f1)



main()
