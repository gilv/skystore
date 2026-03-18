use std::pin::Pin;
use bytes::Bytes;
use s3s::dto::StreamingBlob;
use s3s::stream::ByteStream;
use s3s::stream::RemainingLength;
use tokio::sync::mpsc;
use tokio_stream::Stream;
use tokio_stream::StreamExt;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tracing::{debug, error, info};

/// A wrapper around a stream that adds ByteStream trait with size hint
struct StreamWithSizeHint<S>
where
    S: Stream<Item = Result<Bytes, Box<dyn std::error::Error + Send + Sync>>> + Unpin,
{
    inner: S,
    size_hint: Option<usize>,
}

impl<S> StreamWithSizeHint<S>
where
    S: Stream<Item = Result<Bytes, Box<dyn std::error::Error + Send + Sync>>> + Unpin,
{
    fn new(inner: S, size_hint: Option<usize>) -> Self {
        Self { inner, size_hint }
    }
}

impl<S> Stream for StreamWithSizeHint<S>
where
    S: Stream<Item = Result<Bytes, Box<dyn std::error::Error + Send + Sync>>> + Unpin,
{
    type Item = Result<Bytes, Box<dyn std::error::Error + Send + Sync>>;

    fn poll_next(
        mut self: Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<Option<Self::Item>> {
        Pin::new(&mut self.inner).poll_next(cx)
    }
}

impl<S> ByteStream for StreamWithSizeHint<S>
where
    S: Stream<Item = Result<Bytes, Box<dyn std::error::Error + Send + Sync>>> + Unpin,
{
    fn remaining_length(&self) -> RemainingLength {
        match self.size_hint {
            Some(size) => RemainingLength::new_exact(size),
            None => RemainingLength::new_exact(0),
        }
    }
}

/// Split a streaming blob into multiple independent streams using channels.
/// This is a robust implementation that handles errors properly and works for all object sizes.
pub fn split_streaming_blob(incoming: StreamingBlob, num_splits: usize) -> Vec<StreamingBlob> {
    // Optimization: if no splitting needed, return original stream
    if num_splits == 0 {
        return vec![];
    }
    
    if num_splits == 1 {
        debug!("No splitting needed, returning original stream");
        return vec![incoming];
    }
    
    debug!("Splitting stream into {} copies", num_splits);
    
    // Get size hint from incoming stream and extract the exact value if available
    let size_hint_value = incoming.remaining_length().exact();
    
    // Create channels for each split
    let mut senders = Vec::new();
    let mut result = Vec::new();
    
    for i in 0..num_splits {
        let (tx, rx) = mpsc::unbounded_channel();
        senders.push(tx);
        
        // Wrap receiver in a stream with proper size hint
        let stream = UnboundedReceiverStream::new(rx);
        let wrapped = StreamWithSizeHint::new(stream, size_hint_value);
        let blob = StreamingBlob::new(wrapped);
        result.push(blob);
        
        debug!("Created stream split {}/{}", i + 1, num_splits);
    }
    
    // Spawn task to read from source and broadcast to all subscribers
    tokio::spawn(async move {
        let mut stream = incoming;
        let mut total_bytes = 0u64;
        let mut chunk_count = 0u64;
        
        info!("Starting stream broadcast to {} subscribers", num_splits);
        
        while let Some(chunk_result) = stream.next().await {
            match chunk_result {
                Ok(chunk) => {
                    let chunk_size = chunk.len();
                    total_bytes += chunk_size as u64;
                    chunk_count += 1;
                    
                    // Send to all subscribers
                    let mut failed_senders = Vec::new();
                    for (idx, sender) in senders.iter().enumerate() {
                        if let Err(e) = sender.send(Ok(chunk.clone())) {
                            error!(
                                "Failed to send chunk {} ({} bytes) to subscriber {}: {:?}",
                                chunk_count, chunk_size, idx, e
                            );
                            failed_senders.push(idx);
                        }
                    }
                    
                    // If any sender failed, subscribers have disconnected
                    if !failed_senders.is_empty() {
                        error!(
                            "Subscribers {:?} disconnected after {} bytes, aborting broadcast",
                            failed_senders, total_bytes
                        );
                        
                        // Send error to remaining subscribers
                        for (idx, sender) in senders.iter().enumerate() {
                            if !failed_senders.contains(&idx) {
                                let _ = sender.send(Err(Box::new(std::io::Error::new(
                                    std::io::ErrorKind::BrokenPipe,
                                    "One or more subscribers disconnected"
                                ))));
                            }
                        }
                        break;
                    }
                    
                    if chunk_count % 100 == 0 {
                        debug!(
                            "Broadcast progress: {} chunks, {} bytes to {} subscribers",
                            chunk_count, total_bytes, num_splits
                        );
                    }
                }
                Err(e) => {
                    error!(
                        "Stream error after {} bytes ({} chunks): {:?}",
                        total_bytes, chunk_count, e
                    );
                    
                    // Send error to all subscribers
                    for sender in &senders {
                        let _ = sender.send(Err(Box::new(std::io::Error::new(
                            std::io::ErrorKind::Other,
                            format!("Source stream error: {:?}", e)
                        ))));
                    }
                    break;
                }
            }
        }
        
        info!(
            "Stream broadcast completed: {} bytes in {} chunks to {} subscribers",
            total_bytes, chunk_count, num_splits
        );
        
        // Channels will be closed when senders are dropped
    });
    
    result
}

#[cfg(test)]
mod test_flo {
    use super::*;

    use s3s::Body;

    #[tokio::test]
    async fn test_flo() {
        async fn test_sub_blob(sub_blob: StreamingBlob, expected_body: Vec<u8>) {
            let result_bytes = sub_blob
                .map(|chunk| chunk.unwrap())
                .collect::<Vec<_>>()
                .await;
            let body = result_bytes.concat();
            assert!(body == expected_body);
        }

        let blob: StreamingBlob = StreamingBlob::from(Body::from("hello world".to_string()));

        let mut out = split_streaming_blob(blob, 2);
        assert!(out.len() == 2);

        let sub_blob1 = out.pop().unwrap();
        let sub_blob2 = out.pop().unwrap();

        test_sub_blob(sub_blob1, "hello world".to_string().into_bytes()).await;
        test_sub_blob(sub_blob2, "hello world".to_string().into_bytes()).await;
    }
}
