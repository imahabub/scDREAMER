import tensorflow as tf
import scanpy as sc
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import LabelEncoder
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.cluster import normalized_mutual_info_score as nmi


# Leaky Relu
def lrelu(x, alpha = 0.2, name='lrelu'):
    return tf.maximum(x, alpha*x)

def dense(x, inp_dim, out_dim, name = 'dense'):

    with tf.variable_scope(name, reuse=None): # earlier only tf
        weights = tf.get_variable("weights", shape=[inp_dim, out_dim],
                                  initializer = tf.contrib.layers.xavier_initializer()) # contrib
        
        bias = tf.get_variable("bias", shape=[out_dim], initializer = tf.constant_initializer(0.0))
        
        # initializer= tf2.initializers.GlorotUniform(); same as Xavier's initializer; tf.contrib.layers.xavier_initializer()    
        out = tf.add(tf.matmul(x, weights), bias, name='matmul')
        return out


#AJ: 20 may
# Zero-inflated negative binomial (ZINB) model is for modeling count variables with excessive zeros and it is usually for overdispersed count outcome variables.
def zinb_model(self, x, mean, inverse_dispersion, logit, eps=1e-4): 

    # 1e8 should be of same dimensions as other parameters....                 
    expr_non_zero = - tf.nn.softplus(- logit) \
                    + tf.log(inverse_dispersion + eps) * inverse_dispersion \
                    - tf.log(inverse_dispersion + mean + eps) * inverse_dispersion \
                    - x * tf.log(inverse_dispersion + mean + eps) \
                    + x * tf.log(mean + eps) \
                    - tf.lgamma(x + 1) \
                    + tf.lgamma(x + inverse_dispersion) \
                    - tf.lgamma(inverse_dispersion) \
                    - logit 
    
    expr_zero = - tf.nn.softplus( - logit) \
                + tf.nn.softplus(- logit + tf.log(inverse_dispersion + eps) * inverse_dispersion \
                                  - tf.log(inverse_dispersion + mean + eps) * inverse_dispersion) 

    template = tf.cast(tf.less(x, eps), tf.float32)
    expr =  tf.multiply(template, expr_zero) + tf.multiply(1 - template, expr_non_zero)
    return tf.reduce_sum(expr, axis=-1)

    
def eval_cluster_on_test(self,ep):
    # Embedding points in the test data to the latent space
    inp_encoder = self.data_test
    # labels = self.labels_test
    batch_label = self.batch_test
            
    latent_matrix = self.sess.run(self.z, feed_dict = {self.x_input: inp_encoder, self.batch_input: batch_label, self.keep_prob: 1.0})
    
    # print ('latent_matrix shape', latent_matrix.shape)
    # print (labels.shape)
    
    Ann = sc.AnnData(inp_encoder)
    Ann.obsm['final_embeddings'] = latent_matrix
    # Ann.obs['group'] = labels.astype(str)
    
    #sc.pp.neighbors(Ann, use_rep = 'final_embeddings') #use_rep = 'final_embeddings'
    #sc.tl.umap(Ann)
    #img = sc.pl.umap(Ann, color = 'group', frameon = False) # cells
    #print(img)
    
    np.savetxt('latent_matrix_c'+str(ep)+'.csv', latent_matrix, delimiter=",")
    
    #Ann.obs['batch'] = self.batch_info.astype(str)
    #img2 = sc.pl.umap(Ann, color = self.batch, frameon = False)
    #print(img2)

    # K = np.size(np.unique(labels))   
    # kmeans = KMeans(n_clusters=K, random_state=0).fit(latent_matrix)
    # y_pred = kmeans.labels_

    # print('Computing NMI ...')
    # NMI = nmi(labels.flatten(), y_pred.flatten())
    # print('Done !')

    # print('NMI = {}'. 
          # format(NMI)) 

def read_h5ad(data_path, batch, hvg=2000):
    print('updated hvg')
    Ann = sc.read_h5ad(data_path)
    Ann.layers["counts"] = Ann.X.copy()

    sc.pp.normalize_total(Ann, target_sum=1e4)
    sc.pp.log1p(Ann)
    Ann.raw = Ann 
    
    sc.pp.highly_variable_genes(
        Ann, 
        flavor="seurat", 
        n_top_genes=hvg,
        batch_key=batch,
        subset=True)

    if type(Ann.X) != type(np.array([])):
        Ann.X = Ann.X.todense()
    data = Ann.X 

    #AJ: Convert to categorical instead of this...
    t_ = Ann.obs[batch] #.to_list()
    batch_info = np.array([[i] for i in t_]) # for other datasets

    #batch_info = np.array(Ann.obs[batch].astype("category").reset_index(drop = True)).reshape(-1,1) 
    enc = OneHotEncoder(handle_unknown='ignore')
    #batch_info_enc = enc.fit_transform(batch_info).toarray()
  
    enc.fit(batch_info.reshape(-1, 1))
    batch_info_enc = enc.transform(batch_info.reshape(-1, 1)).toarray()

    return data, batch_info_enc, batch_info
    

def load_gene_mtx(dataset_name, batch, transform = True, count = True, actv = 'sig'):

    data, batch_info_enc, batch_info = read_h5ad(dataset_name, batch)
         
    if count == False:
        data = np.log2(data+1)

        if actv == 'lin':
            scale = 1.0
        else:
            scale = np.max(data)
        data = data / scale           

    ord_enc = LabelEncoder()
    # labels  = ord_enc.fit_transform(labels)
    # print ('here', labels)

    # unique, counts = np.unique(labels, return_counts = True)
    # dict(zip(unique, counts))
    
    total_size = data.shape[0]

    if count == False:
        return data, data, scale, batch_info_enc, batch_info_enc, batch_info

    return data, data
