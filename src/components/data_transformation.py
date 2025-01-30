import os
import sys
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from imblearn.combine import SMOTETomek
from dataclasses import dataclass

from src.exception import CustomException
from src.logger import logging
from src.utils import save_object

@dataclass
class DataTransformationConfig:
    preprocessor_obj_file_path=os.path.join("artifacts", "preprocessor.pkl")
    smote_tomek_obj_file_path=os.path.join("artifacts", "smotetomek.pkl")

# Custom LabelEncoding Transformer
class LabelEncodingTransformer(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.encoders = {}  # Store separate encoders for each column
    
    def fit(self, X, y=None):
        """
        Fit a separate LabelEncoder for each categorical column in X.
        """
        # Check if X is a pandas DataFrame
        if isinstance(X, pd.DataFrame):
            for col in X.columns:
                # Check if column is categorical (non-numeric)
                if X[col].dtype == 'object' or X[col].dtype.name == 'category':
                    self.encoders[col] = LabelEncoder()
                    self.encoders[col].fit(X[col])
        else:
            # Handle numpy.ndarray case
            # Ensure that you have column names if working with numpy arrays
            self.original_columns = [f"col_{i}" for i in range(X.shape[1])]
            for i in range(X.shape[1]):
                # Manually encode categorical columns if indices are known
                if isinstance(X[:, i], np.ndarray) and not np.issubdtype(X[:, i].dtype, np.number):
                    self.encoders[i] = LabelEncoder()
                    self.encoders[i].fit(X[:, i])
        return self
    
    def transform(self, X):
        """
        Transform each categorical column using its corresponding LabelEncoder.
        """
        # Check if X is a pandas DataFrame
        if isinstance(X, pd.DataFrame):
            X_encoded = X.copy()
            for col in X.columns:
                # Apply transformation only to categorical columns
                if col in self.encoders:
                    X_encoded[col] = self.encoders[col].transform(X[col])
            return X_encoded
        else:
            # Handle numpy.ndarray case
            X_encoded = X.copy()
            for i in range(X.shape[1]):
                # Apply transformation only to columns that have a stored encoder
                if i in self.encoders:
                    X_encoded[:, i] = self.encoders[i].transform(X[:, i])
            return X_encoded
        
class DataTransformation:
    def __init__(self):
        self.data_transformation_config = DataTransformationConfig()
    
    def get_data_transformer_object(self):
        '''
        This function si responsible for data trnasformation
        '''
        try:
            logging.info(
                "Entered get_data_transformer_object method of DataTransformation class"
            )
            
            numerical_columns = [
                'Air temperature K',
                'Process temperature K',
                'Rotational speed rpm',
                'Torque Nm',
                'Tool wear min'
            ]
            categorical_columns = ['Type']
            
            num_pipeline = Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler())
                ]
            )
            
            cat_pipeline = Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("label_encoding", LabelEncodingTransformer()),
                    ("scaler", StandardScaler(with_mean=False))
                ]
            )
            
            logging.info(f"Categorical columns: {categorical_columns}")
            logging.info(f"Numerical columns: {numerical_columns}")
            
            preprocessor = ColumnTransformer(
                transformers=[
                    ("num_pipeline", num_pipeline, numerical_columns),
                    ("cat_pipeline", cat_pipeline, categorical_columns)
                ]
            )
            
            return preprocessor
            
        except Exception as e:
            raise CustomException(e, sys)
        
    def initiate_data_transformation(self, train_path, test_path):
        try:
            train_df=pd.read_csv(train_path)
            test_df=pd.read_csv(test_path)

            logging.info("Read train and test data completed")

            logging.info("Obtaining preprocessing object")

            preprocessing_obj=self.get_data_transformer_object()

            target_column_name='Failure Type'

            input_feature_train_df=train_df.drop(columns=[target_column_name], axis=1)
            target_feature_train_df=train_df[target_column_name]
            print(target_feature_train_df)

            input_feature_test_df=test_df.drop(columns=[target_column_name], axis=1)
            target_feature_test_df=test_df[target_column_name]

            logging.info(
                f"Applying preprocessing object on training dataframe and testing dataframe."
            )

            input_feature_train_arr=preprocessing_obj.fit_transform(input_feature_train_df)
            input_feature_test_arr=preprocessing_obj.transform(input_feature_test_df)

            # Apply Label Encoding to the target column
            label_encoder = LabelEncoder()
            target_feature_train_df = label_encoder.fit_transform(target_feature_train_df)
            target_feature_test_df = label_encoder.transform(target_feature_test_df)

            # Print the Label Encoding Mapping
            logging.info(f"Label Encoding Mapping for Target Column:")
            logging.info(f"{dict(zip(label_encoder.classes_, range(len(label_encoder.classes_))))}")

            # Apply SMOTETomek to handle class imbalance in the target column
            smote_tomek_obj = SMOTETomek(random_state=42)

            # Apply SMOTETomek on the train data (not test data)
            input_feature_train_resampled_arr, target_feature_train_resampled_arr = smote_tomek_obj.fit_resample(input_feature_train_arr, np.array(target_feature_train_df))

            train_arr = np.c_[
                input_feature_train_resampled_arr, target_feature_train_resampled_arr
            ]
            test_arr = np.c_[input_feature_test_arr, np.array(target_feature_test_df)]

            # save_object(
            #     file_path=self.data_transformation_config.preprocessor_obj_file_path,
            #     obj=preprocessing_obj
            # )
            # save_object(

            #     file_path=self.data_transformation_config.smote_tomek_obj_file_path,
            #     obj=smote_tomek_obj

            # )

            logging.info(f"Saved preprocessing and SMOTETomek objects.")

            return (
                    train_arr,
                    test_arr,
                    self.data_transformation_config.preprocessor_obj_file_path,
                )
        except Exception as e:
                raise CustomException(e,sys)

if __name__=="__main__":
    obj=DataTransformation()
    obj.initiate_data_transformation("/mnt/c/Users/HP/ml_projects/maintenance/artifacts/train.csv", "/mnt/c/Users/HP/ml_projects/maintenance/artifacts/test.csv")


