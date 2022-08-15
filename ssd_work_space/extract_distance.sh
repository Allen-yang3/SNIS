#python converge_test.py -dis test/100us_16KB_10:1_x2_net-ssd/1,test/100us_16KB_10:1_x2_net-ssd/2 >> test/100us_16KB_10:1_x2_net-ssd/distance.csv
#python converge_test.py -dis test/100us_16KB_10:1_x2_net-ssd/3,test/100us_16KB_10:1_x2_net-ssd/2 >> test/100us_16KB_10:1_x2_net-ssd/distance.csv
#python converge_test.py -dis test/100us_16KB_10:1_x2_net-ssd/3,test/100us_16KB_10:1_x2_net-ssd/4 >> test/100us_16KB_10:1_x2_net-ssd/distance.csv
#python converge_test.py -dis test/100us_16KB_10:1_x2_net-ssd/5,test/100us_16KB_10:1_x2_net-ssd/4 >> test/100us_16KB_10:1_x2_net-ssd/distance.csv
#python converge_test.py -dis test/100us_16KB_10:1_x2_net-ssd/5,test/100us_16KB_10:1_x2_net-ssd/6 >> test/100us_16KB_10:1_x2_net-ssd/distance.csv

python converge_test.py -dis test/1,test/2 >> test/distance.csv
python converge_test.py -dis test/3,test/2 >> test/distance.csv
python converge_test.py -dis test/3,test/4 >> test/distance.csv
python converge_test.py -dis test/5,test/4 >> test/distance.csv
python converge_test.py -dis test/5,test/6 >> test/distance.csv
